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
from PastSessions.PastSessionManager import PastSessionManager

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

class SystemDatabaseManager:

    def __init__(self):
        self.db_manager: IDataBaseManager = DataBaseManager()

    def authenticate(self, token):
        if not token:
            return None
        return self.db_manager.authenticate(token)

    def create_user(self, user_id, token):
        self.db_manager.create_user(user_id=user_id,token=token)

    def get_users(self):
        return self.db_manager.get_users()

    def save_session(self, user_id, session_summary):
        self.db_manager.save_session(user_id,session_summary)

    def get_history(self, user_id):
        return self.db_manager.get_history(user_id)

    def get_session_details(self, user_id, session_id):
        return self.db_manager.get_session_details(user_id,session_id)
    def get_legacy_sources(self, user_id):
        return self.db_manager.get_legacy_sources(user_id)
    
class SessionSummaryManager:
    def __init__(self, db_manager):
        self.past_session_manager = PastSessionManager()
        self.db_manager = db_manager
        self.clock = datetime.now

    def _details(self, user_id, sid):
        return self.db_manager.get_session_details(user_id,str(sid)) 
    
    def get_past_session(self,action,content,user_id,manager):
        if action in ('get_session_details','get_session_summary'):
            details = self._details(user_id,content.get('session_id'))
            if action == 'get_session_details':
                return details
            return {**details['summary'],'storage_status': details['storage_status']}
        if action not in ('get_sessions','get_past_sessions','get_stats','export_activity'):
            raise ValueError('Unknown action')
        records = {session['id']: session for session in self.db_manager.get_history(user_id)}
        sessions = sorted(records.values(),key=lambda session: session['started_at'],reverse=True)
        legacy = (self.db_manager.get_legacy_sources(user_id) if action == 'export_activity' else [])
        return self.past_session_manager.present(
            action,
            sessions,
            set(),
            legacy,
            self.clock()
        )
