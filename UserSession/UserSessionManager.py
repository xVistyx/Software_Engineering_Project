from interfaces import IUserSessionCoordinator
from .SessionStart import SessionStart, SessionInfo
from .UserSessionDataManager import UserSessionDataManager
from .MetadataProcessing.MetaDataManager import WebsiteMetadataEvaluator
from .MetadataProcessing.SessionInterfaces import IWebsiteMetadataEvaluator
from .AIEval.AISessionEval import AISessionEval
from .StopSession.StopSession import StopSession
from .StopSession.GenerateSummary import SessionSummaryForDB
from dataclasses import asdict
from datetime import datetime
from copy import deepcopy
from threading import RLock



from .ActiveUserSession import ActiveUserSessionManager

class UserSessionCoordinator(IUserSessionCoordinator):
    def __init__(self, session_folder=None, clock=None):
        """Coordinate session components; System serializes calls with this user's lock."""
        self.active_session: SessionInfo = None
        self.ai_eval = AISessionEval() #needs an interface
        self.website_meta_data_evaluator: IWebsiteMetadataEvaluator = WebsiteMetadataEvaluator()
        self.clock = clock or datetime.now
        self.lock = RLock()
        self.session_start = SessionStart(clock=self.clock)
        self.user_session_data_manager = UserSessionDataManager(session_folder)
        self.stop_session = StopSession()
        
        self.active_user_session = ActiveUserSessionManager(self.website_meta_data_evaluator, self.ai_eval)# -> add interface to this
        self.session_id: int = None
        self.session_summary = None
        self.pending_summaries = {}
        self.pending_frontend = {}
        self.save_error = None
        self._recover_retained()
        #add Website blocking to here as well
        
        
        

        
    def user_session_manager(self, action:str, content:dict) -> dict:
        
        
        if action == "get_active_session":
            return self.get_active_session()
        elif action == "start_session":
            return self.start_user_session(content)
        elif action == "update_session":
            return self.update_user_session(content, "update_session")
        elif action == "end_session":
            return self.end_user_session(content)
        elif action == "log_meta_data":
            return {
                "action": "log_meta_data",
                "content": self.update_user_session(content, "log_meta_data") # naming is a bit weird need to fix. But linked to frontend so cannot rn -> future this will be function call to block the websites
            }

        else:
            return {
                "action": action,
                "content": {
                    "error": "Unknown user session action"
                }
            }
    def start_user_session(self, content:dict) -> dict:
        """This functions main purpose is to log a new session such that the start gets logged in the db"""
        if self.active_session and self.active_session.get('status') in ('running', 'paused'):
            raise ValueError('End the current session before starting another')
        session_start:dict = self.session_start.session_start_as_dict(content)
        session_start.update(status='running', strict_mode=bool(content.get('strict_mode', False)))
        self.website_meta_data_evaluator = WebsiteMetadataEvaluator()
        self.active_user_session = ActiveUserSessionManager(self.website_meta_data_evaluator, self.ai_eval)
        self.user_session_data_manager.create_session_json(session_start["id"])
        self.user_session_data_manager.log_session_start(session_start)
        self.active_session = session_start
        self.session_id = session_start['id']

        return {"action": "start_session","content": session_start}

    def get_active_session(self) -> dict:

        self.checkpoint()
        if self.active_session is None or self.active_session.get('status') == 'ended':
         
            return {
                "action": "get_active_session",
                "content": {
                    "is_running": False
                }
            }
        #this will return a dictionary with the updated user data
        return {'action': 'get_active_session', 'content': self.active_session}
   


    
    def update_user_session(self, content: dict, command: str):

        if command == "log_meta_data":
            if not self.active_session or not self.active_session['is_running']:
                return {'stored': False}
            if str(content.get('session_id')) != str(self.session_id) or content.get('incognito'):
                return {'stored': False}
            topic = self.active_session["topic"]
            metadata_result, stored = (self.active_user_session.active_session_manager(content,topic))
            if not stored:
                return {'stored': False}
            self.set_db_session_data(metadata_result, True)
            return {'stored': True}
        else:
            if self.active_session['strict_mode']:
                raise ValueError('Strict sessions cannot be paused or ended early')
            status = content.get('status')
            if status not in ('running', 'paused'):
                raise ValueError('Session status must be paused or running')
            self.checkpoint()
            if self.active_session['status'] == 'ended':
                return {'action': 'update_session', 'content': self.active_session}
            previous = deepcopy(self.active_session)
            self._flush_metadata(stop=True)
            self.active_session.update(status=status, is_running=status == 'running', last_update_time=self.clock())
            try:
                self.user_session_data_manager.log_session_start(self.active_session)
            except Exception:
                self.active_session = previous
                raise
            return {'action': 'update_session', 'content': self.active_session}
         
            


    def end_user_session(self, frontend_content:dict ) -> dict:
        if self.session_id in self.pending_summaries:
            return self.pending_frontend[self.session_id]
        if self.active_session is None:
            raise ValueError('Session not found')
        if self.active_session.get('strict_mode') and not frontend_content.get('_timer_finished'):
            raise ValueError('Strict sessions cannot be paused or ended early')
        self._flush_metadata(stop=True)
        previous = deepcopy(self.active_session)
        ended = frontend_content.get('_ended_at') or self.clock()
        self.active_session.update(actual_end_time=ended, last_update_time=ended,
                                   is_running=False, status='ended')
        try:
            self.user_session_data_manager.log_session_start(self.active_session)
        except Exception:
            self.active_session = previous
            raise
        session_content = self.get_db_session_data(self.session_id)
        frontend_info, backend_info, session_info = self.stop_session.manage_session_stop(session_content, self.active_session)
        self.user_session_data_manager.save_pending_summary(self.session_id, asdict(backend_info), frontend_info)
        self.session_summary = backend_info
        self.pending_summaries[self.session_id] = backend_info
        self.pending_frontend[self.session_id] = frontend_info
        self.active_session = session_info
        # System confirms the SQL commit before calling delete_old_session.
        return frontend_info


    def send_to_global_db_manager(self):
        return self.session_summary

    def get_session_summary(self):
        ...

    def pause_user_session(self):
        ...
    def delete_old_session(self, session_id=None):
        session_id = self.session_id if session_id is None else session_id
        self.user_session_data_manager.delete_current_session_json(session_id)
        self.pending_summaries.pop(session_id, None)
        self.pending_frontend.pop(session_id, None)

    def _recover_retained(self):
        for data in list(self.user_session_data_manager.retained_sessions()):
            info = data['session_info']
            sid = info['id']
            if 'summary_for_db' not in data:
                info['actual_end_time'] = info.get('actual_end_time') or info['last_update_time']
                info.update(is_running=False, status='ended')
                self.user_session_data_manager.log_session_start(info)
                summary, frontend = self.stop_session.session_summary.generate_summary(data)
                self.user_session_data_manager.save_pending_summary(sid, asdict(summary), frontend)
                data = self.user_session_data_manager.session_end_json(sid)
            fields = data['summary_for_db']
            for name in ('session_start_time', 'session_end_time'):
                fields[name] = datetime.fromisoformat(fields[name])
            self.pending_summaries[sid] = SessionSummaryForDB(**fields)
            self.pending_frontend[sid] = data['frontend_summary']

    def _flush_metadata(self, stop=False):
        for item in self.website_meta_data_evaluator.snapshot_metadata(stop):
            self.user_session_data_manager.update_metadata_in_session_json(item)

    def checkpoint(self):
        if not self.active_session:
            return
        if self.active_session['status'] == 'ended':
            if self.session_id not in self.pending_summaries and self.user_session_data_manager.session_path:
                self._recover_retained()
            return
        previous = deepcopy(self.active_session)
        now = self.clock()
        expired_at = self.active_user_session.advance_session_clock(self.active_session, now)
        if expired_at is not None:
            self.end_user_session({'_timer_finished': True, '_ended_at': expired_at})
            return
        try:
            self._flush_metadata()
            self.user_session_data_manager.log_session_start(self.active_session)
        except Exception:
            self.active_session = previous
            raise


    def get_db_session_data(self, session_id: int) -> dict:
        """
        This function will be responsible for getting information from the db about current session 
        ONLY ACCESS POINT TO THE USERSESSIONDATAMANAGER to get stuff
        """
        return self.user_session_data_manager.session_end_json(session_id)
        

    def set_db_session_data(self, content: dict | list[dict], log ) -> None:
        """
        
        ONLY ACCESS POINT TO THE USERSESSIONDATAMANAGER to set stuff 
        """
        if log == False:
            self.active_user_session.updated_session_state(content)
        else:
            if isinstance(content, dict):
                print("NEW TAB -> WRITING")
                self.user_session_data_manager.write_metadata_to_session_json(content)
            
            elif isinstance(content, list):
                for changed_tab in content:
                    self.user_session_data_manager.update_metadata_in_session_json(changed_tab)
        

        


"""
We still need a way to end the session
-> needs to clear the db etc to not make the software to intensive to run
"""        


     

"""
# start_session
{
    "action": "start_session",
    "content": {
        "id": "test-session-123"
    }
}
# update_session
{
    "action": "update_session",
    "content": {}
}
# end_session
{
    "action": "end_session",
    "content": {}
}

"""
