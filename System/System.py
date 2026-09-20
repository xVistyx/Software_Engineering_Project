from interfaces import IServerManage, IUserSessionCoordinator, IUserSessionCoordinator, ISettings, IPastSessionManager
from .BackendRequests import BackendRequests, SessionData, FrontEndSessionData 
from UserSession.UserSessionManager import UserSessionCoordinator
#from UserSession.UserSessionDataManager import UserSessionDataManager
from Settings.Settings import Settings
#from PastSessions.PastSessionManager import PastSessionManager

from .SystemManager import SetupSystem, SystemDatabaseManager, SessionSummaryManager


class System():
    def __init__(self):
        self.activity_path = None
        self.system_manager = SetupSystem(activity_path=self.activity_path)
        self.server_manager:IServerManage = None
        self.backend_requests: BackendRequests = BackendRequests()
        self.data_manager = self.system_manager.system_db_manager
        self.session_summary_manager = SessionSummaryManager(self.data_manager)
        
        self.frontend_message: FrontEndSessionData = {}

        self.settings:ISettings = Settings()
        self.is_session_active = False
        
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}
        
        self.features = {
        "start_session": self.run_user_session,
        "update_session": self.run_user_session,
        "end_session": self.run_user_session,
        "get_active_session": self.run_user_session,

        "get_settings": self.run_settings,
        "update_settings": self.run_settings,
        "get_blocklist": self.run_settings,
        "update_blocklist": self.run_settings,

        "get_session_summary": self.run_past_session,
        "get_session_details": self.run_past_session,
        "get_sessions": self.run_past_session,
        "get_stats": self.run_past_session,

        "log_meta_data": self.run_user_session,
    } 
        
    def authenticate_user(self, token) -> tuple[str, IUserSessionCoordinator]:
        identity = self.data_manager.authenticate(token)
        if identity is None:
            raise ValueError("Invalid token")
        user_id = identity["user_id"]
        user_session_manager = (self.system_manager.user_manager.for_user(user_id))
        return user_id, user_session_manager

        
        

   
    def buildResponse(self, frontend_message:dict, token: str) ->SessionData :
            """build response from backend"""
            action = frontend_message["action"]
            content = frontend_message["content"]
            print("frontend message ", frontend_message) 
            user_id, user_session_manager = self.authenticate_user(token)
            if user_session_manager is None:
                raise ValueError("User session manager is None")
            try:
                handler = self.features[action]
            except KeyError:
                raise ValueError(f"Unknown action: {action}")
            return handler(action, content, user_id, user_session_manager)

    #BackEnd -> Frontend  

    def send_requests_to_frontend(self, message: dict) -> SessionData:
        return self.backend_requests.build_responses(message)
        
        
    def run_user_session(self,action: str,content: dict,user_id,user_session_manager) -> dict:

        response = user_session_manager.user_session_manager(action,content)

        if action == "end_session":
            session_summary = (user_session_manager.send_to_global_db_manager())
            self.data_manager.save_session(user_id,session_summary)
            return response

        return response


  
    
    
    def run_settings(self,action,content,user_id, user_session_manager) -> dict:
         # must return a dictionary formated: action: str  content: dict
        settings =  self.settings.settings_manager(action=action, content= content)
        return settings

    


    def run_past_session(
    self,
    action,
    content,
    user_id,
    manager
):
        result = self.session_summary_manager.get_past_session(
            action,
            content,
            user_id,
            manager
        )

        return {
            "action": action,
            "content": result
        }



