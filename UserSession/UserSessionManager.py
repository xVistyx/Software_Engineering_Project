from threading import RLock
from interfaces import IUserSessionCoordinator
from .SessionStart import SessionStart, SessionInfo
from .UserSessionDataManager import UserSessionDataManager
from .MetadataProcessing.MetaDataManager import WebsiteMetadataEvaluator
from .MetadataProcessing.SessionInterfaces import IWebsiteMetadataEvaluator
from .AIEval.AISessionEval import AISessionEval
from .StopSession.StopSession import StopSession
from .BlockingWebsites.WebsiteBlockerManager import WebsiteBlockerManager


from .ActiveUserSession import ActiveUserSessionManager

class UserSessionCoordinator(IUserSessionCoordinator):
    def __init__(self, session_folder, clock):
        """I need to add threading to this to make it threading safe. This file shouldnt do anything but coordinate. Logic is handeled in the manager Files"""

        self.lock = RLock()
        self.block_events = set()
        self.active_session: SessionInfo = None
        self.ai_eval = AISessionEval() #needs an interface
        self.website_meta_data_evaluator: IWebsiteMetadataEvaluator = WebsiteMetadataEvaluator()
        self.session_start:SessionInfo = SessionStart()
        self.user_session_data_manager = UserSessionDataManager()# -> add interface to this
        self.stop_session = StopSession()
        self.website_blocking_manager = WebsiteBlockerManager(self.ai_eval)
        self.active_user_session = ActiveUserSessionManager(self.website_meta_data_evaluator, self.ai_eval, self.website_blocking_manager)# -> add interface to this
        self.session_id: int = None
        self.session_summary = None
       
        
        
        

        
    def user_session_manager(self, action:str, content:dict) -> dict:
      
        
        with self.lock:
            return self._dispatch(action, content)

    def _dispatch(self, action, content):
        if action in {"log_meta_data", "log_dynamic_content", "update_session"}:
            if not self.active_session or not self.active_session["is_running"] or content.get("session_id") != self.session_id:
                return {"action": action, "content": {"ignored": True}}
        if action == "end_session" and (not self.active_session or not self.active_session["is_running"] or (content.get("session_id") is not None and content["session_id"] != self.session_id)):
            return {"action": action, "content": {"error": "No matching active session"}}
        if action == "get_active_session":
            return self.get_active_session()
        elif action == "start_session":
            return self.start_user_session(content)
        elif action == "update_session":
            return self.update_user_session(content, "update_session")
        elif action == "end_session":
            return self.end_user_session(content)
        elif action =="log_dynamic_content":
            return {"action": action,"content": self.update_user_session(content, "log_dynamic_content") # naming is a bit weird need to fix. But linked to frontend so cannot rn -> future this will be function call to block the websites
            }
        elif action == "log_meta_data":
            return {"action": action,"content": self.update_user_session(content, "log_meta_data") # naming is a bit weird need to fix. But linked to frontend so cannot rn -> future this will be function call to block the websites
                        }
        else:
            return {"action": action,"content": {"error": "Unknown user session action"}}
        
    def start_user_session(self, content:dict) -> dict:
        """This functions main purpose is to log a new session such that the start gets logged in the db"""

        
        session_start:dict = self.session_start.session_start_as_dict(content)

        
        self.website_meta_data_evaluator = WebsiteMetadataEvaluator()
        self.active_user_session = ActiveUserSessionManager(self.website_meta_data_evaluator, self.ai_eval, self.website_blocking_manager)
        self.block_events.clear()
        self.session_summary = None
        self.active_session:SessionInfo = session_start
        print("Active session ", session_start)
        self.session_id = session_start["id"]
        self.user_session_data_manager.create_session_json(session_start["id"])
        self.user_session_data_manager.log_session_start(session_start)

        return {"action": "start_session","content": session_start}

    def get_active_session(self) -> dict:

        if self.active_session is None:
         
            return {
                "action": "get_active_session",
                "content": {
                    "is_running": False
                }
            }
        #this will return a dictionary with the updated user data
        return self.active_user_session.updated_session_state(self.active_session)
   


    
    def update_user_session(self, content: dict, command: str):
        frontend_message = {}
        if command == "log_meta_data" and content.get("reason") == "website_blocked":
            event_id = content.get("event_id")
            if event_id and event_id not in self.block_events:
                self.block_events.add(event_id)
                self.active_session["blocked_tabs"] = len(self.block_events)
                self.user_session_data_manager.update_blocked_count(len(self.block_events))
                # Only close the matching visit, not a later page in the same tab.
                self.set_db_session_data(self.website_meta_data_evaluator.blocked_visit(content), True)
            return {"blocked_tabs": len(self.block_events)}
        if command == "log_dynamic_content":
            topic = self.active_session["topic"]
            metadata_result, stored, frontend_message = (self.active_user_session.active_session_manager(content,topic, "log_dynamic_content"))
        elif command == "log_meta_data":
            topic = self.active_session["topic"]
            metadata_result, stored, frontend_message = (self.active_user_session.active_session_manager(content,topic, "log_meta_data"))
            if not stored:
                return frontend_message
            self.set_db_session_data(metadata_result, True)
        else:
            self.set_db_session_data(content, False)
        return frontend_message
         
            


    def end_user_session(self, frontend_content: dict) -> dict:
        self.set_db_session_data(self.website_meta_data_evaluator.finish(), True)
        self.user_session_data_manager.update_blocked_count(len(self.block_events))
        session_content = self.get_db_session_data(self.session_id)

        frontend_info, backend_info, session_info = (
            self.stop_session.manage_session_stop(
                session_content,
                self.active_session
            )
        )

        self.session_summary = backend_info
        self.active_session = session_info

        self.session_start.mark_session_stopped()  # ADD THIS

        return frontend_info


    def send_to_global_db_manager(self):
        return self.session_summary
   
    

    def pause_user_session(self):
        ...
    def delete_old_session(self):
        self.user_session_data_manager.delete_current_session_json()


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
                    self.user_session_data_manager.write_metadata_to_session_json(changed_tab)
        

        
