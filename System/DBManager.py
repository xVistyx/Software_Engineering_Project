import hashlib
import logging
import os
import secrets
import sqlite3
import uuid

from datetime import datetime
from pathlib import Path
from threading import RLock

from DataBase.DataBaseManager import DataBaseManager
from DataBase.IDataBaseManager import IDataBaseManager
from UserSession.UserSessionManager import UserSessionCoordinator
from System.BackendRequests import BackendRequests
from PastSessions.PastSessionManager import PastSessionManager
from Settings.Settings import Settings


class SetupSystem:

    def __init__(self, user_id=None, activity_path=None):

        self.system_db_manager = SystemDatabaseManager()

        configured = (activity_path or os.environ.get("GROVE_ACTIVITY_PATH"))

        if configured:
            self.session_folder = (Path(configured).parent / "team-active")
        else:
            self.session_folder = (Path(__file__).resolve().parents[1]/ "UserSession"/ "ActiveSessionDB")

        self.clock = datetime.now
        self.lock = RLock()

        self.session_managers = {}

        self.backend_requests = BackendRequests()
        self.past_session_manager = PastSessionManager()
        self.settings = Settings()

        self.user_id = user_id

        self.user_manager = AuthenticateUser(
            system_db_manager=self.system_db_manager,
            session_folder=self.session_folder,
            session_managers=self.session_managers,
            lock=self.lock,
            clock=self.clock
        )

    def setup_system(self):

        if self.user_id is None:
            return self.user_manager.register_user()

        manager = self.user_manager.for_user(self.user_id)

        return manager

    def checkpoint(self):

        with self.lock:managers = list(self.session_managers.items())

        for user_id, manager in managers:

            try:
                with manager.lock:
                    manager.checkpoint()
                    self.system_db_manager.save_pending(user_id,manager)

            except Exception:

                logging.exception("Could not checkpoint user %s; will retry",user_id)
class SystemDatabaseManager:

    def __init__(self):
        self.db_manager: IDataBaseManager = DataBaseManager()

    def authenticate(self, token):
        if not token:
            return None

        return self.db_manager.authenticate(token)

    def create_user(self, user_id, token):
        self.db_manager.create_user(
            user_id=user_id,
            token=token
        )

    def get_users(self):
        return self.db_manager.get_users()

    def save_session(self, user_id, session_summary):
        self.db_manager.save_session(
            user_id,
            session_summary
        )


class AuthenticateUser:

    def __init__(self,system_db_manager,session_folder,session_managers,lock,clock):
        self.system_db_manager = system_db_manager
        self.session_folder = session_folder
        self.session_managers = session_managers
        self.lock = lock
        self.clock = clock

    def for_user(self, user_id):
        with self.lock:
            if user_id not in self.session_managers:

                if user_id not in self.system_db_manager.get_users():
                    raise ValueError("Unknown user")

                folder = (
                    self.session_folder
                    / hashlib.sha256(user_id.encode()).hexdigest()
                )

                manager = UserSessionCoordinator(
                    session_folder=folder,
                    clock=self.clock
                )

                self.session_managers[user_id] = manager

            return self.session_managers[user_id]

    def register_user(self):

        user_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)

        self.system_db_manager.create_user(
            user_id=user_id,
            token=token
        )

        self.for_user(user_id)

        return {"token": token}

    
class AuthorizationError(Exception):
    pass

"""
class System(ISystem):
    

    def __init__(self, db_manager: IDataBaseManager = None, activity_path=None, clock=None):
        self.db_manager = db_manager if db_manager is not None else DataBaseManager()
        configured = activity_path or os.environ.get('GROVE_ACTIVITY_PATH')
        self.session_folder = (Path(configured).parent / 'team-active') if configured else (
            Path(__file__).resolve().parents[1] / 'UserSession' / 'ActiveSessionDB')
        self.clock = clock or datetime.now
        self.lock = RLock()
        self.session_managers = {}
        self.backend_requests = BackendRequests()
        self.past_session_manager = PastSessionManager()
        self.settings = Settings()
        for user_id in self.db_manager.get_users():
            self.for_user(user_id)

    

    

    def handle_request(self, message, identity):
        action, content = message['action'], message['content']
        if not identity or identity.get('role') not in {'user', 'ai'}:
            raise AuthorizationError('This key does not permit that action')
        if (identity['role'] == 'ai') != (action in self.AI_ACTIONS):
            raise AuthorizationError('This key does not permit that action')
        if 'user_id' in content:
            raise ValueError('Do not supply user_id; the access key determines the owner')
        return self.send_requests_to_frontend(self.buildResponse(message, identity['user_id']))

    def buildResponse(self, message, user_id=None):
        if not user_id:
            raise ValueError('An authenticated user is required')
        action, content = message['action'], message['content']
        if action == 'get_ai_sessions':
            result = [{k: s[k] for k in ('id', 'topic', 'started_at')} for s in self.db_manager.get_history(user_id)]
        elif action == 'get_ai_session':
            result = self.db_manager.get_ai_session(user_id, str(content.get('session_id')))
        elif action == 'save_session_analysis':
            result = self.db_manager.save_session_analysis(user_id, str(content.get('session_id')), content.get('analysis'))
        else:
            manager = self.for_user(user_id)
            with manager.lock:
                manager.checkpoint()
                self._save_pending(user_id, manager)
                if action in self.SESSION_ACTIONS:
                    result = self.run_user_session(action, content, user_id, manager)
                elif action == 'retry_session_saves':
                    result = {'pending': len(manager.pending_summaries), 'message': manager.save_error}
                elif action in ('get_settings', 'get_blocklist', 'update_settings', 'update_blocklist'):
                    data = self.db_manager.get_preferences(user_id, self.settings.DEFAULTS)
                    result = self.settings.handle(action, content, data)
                    if action.startswith('update_'):
                        self.db_manager.save_preferences(user_id, data)
                else:
                    result = self.run_past_session(action, content, user_id, manager)
        return {'action': action, 'content': result}

    def run_user_session(self, action, content, user_id, manager):
        content = dict(content)
        if action == 'start_session':
            settings = self.db_manager.get_preferences(user_id, self.settings.DEFAULTS)['settings']
            content['strict_mode'] = settings['strictMode']
        if action in ('end_session', 'update_session'):
            sid = str(content.get('session_id'))
            active = manager.active_session
            if not active or str(active['id']) != sid or active.get('status') == 'ended':
                details = self._details(user_id, manager, sid)
                return {**details['summary'], 'id': sid, 'storage_status': details['storage_status']}
            # Internal completion flags cannot be supplied by a browser request.
            content = {'session_id': content['session_id'], **({'status': content.get('status')} if action == 'update_session' else {})}
        result = manager.user_session_manager(action, content)['content']
        self._save_pending(user_id, manager)
        if action == 'end_session':
            result = {**result, 'id': str(manager.session_id),
                      'storage_status': 'pending' if manager.session_id in manager.pending_summaries else 'saved'}
        return deepcopy(result)

    def _details(self, user_id, manager, sid):
        pending = next((s for key, s in manager.pending_summaries.items() if str(key) == str(sid)), None)
        if pending is not None:
            session, summary = summary_record(user_id, pending)
            return {'session': session, 'summary': summary, 'analysis': None, 'storage_status': 'pending'}
        return self.db_manager.get_session_details(user_id, str(sid))

    def run_past_session(self, action, content, user_id, manager):
        if action in ('get_session_details', 'get_session_summary'):
            details = self._details(user_id, manager, content.get('session_id'))
            return details if action == 'get_session_details' else {**details['summary'], 'storage_status': details['storage_status']}
        if action not in ('get_sessions', 'get_past_sessions', 'get_stats', 'export_activity'):
            raise ValueError('Unknown action')
        records = {s['id']: s for s in self.db_manager.get_history(user_id)}
        pending_ids = {str(sid) for sid in manager.pending_summaries}
        for summary in manager.pending_summaries.values():
            session, _ = summary_record(user_id, summary)
            records[session['id']] = session
        sessions = sorted(records.values(), key=lambda s: s['started_at'], reverse=True)
        legacy = self.db_manager.get_legacy_sources(user_id) if action == 'export_activity' else []
        return self.past_session_manager.present(action, sessions, pending_ids, legacy, self.clock())

    def send_requests_to_frontend(self, message):
        return self.backend_requests.build_responses(message)
"""
