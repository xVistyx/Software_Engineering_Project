from interfaces import ISystem, IServerManage, IUserSessionManager, IUserSessionManager, ISettings, IPastSessionManager
from .BackendRequests import BackendRequests, SessionData, FrontEndSessionData 
from UserSession.UserSessionManager import UserSessionManager
#from UserSession.UserSessionDataManager import UserSessionDataManager
from Settings.Settings import Settings
from PastSessions.PastSessionManager import PastSessionManager
from DataBase.DataBaseManager import DataManager

class System(ISystem):
    def __init__(self):
       
        self.server_manager:IServerManage = None
        self.data_manager = DataManager()
        self.backend_requests: BackendRequests = BackendRequests()
        self.frontend_message: FrontEndSessionData = {}
        self.user_session_manager: IUserSessionManager = UserSessionManager()
        self.settings:ISettings = Settings()
        self.is_session_active = False

        #self.test_dict:dict = {"action": "True", "content": {"True":"true"}}
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}
}
        self.past_sessions: IPastSessionManager= PastSessionManager()
        self.features = {"start_session": self.run_user_session, "update_session": self.run_user_session, "end_session": self.run_user_session, 
                         "get_settings": self.run_settings, "update_settings": self.run_settings, "get_blocklist": self.run_settings,
                         "update_blocklist": self.run_settings,"get_session_summary": self.run_past_session,"get_sessions": self.run_past_session,
                          "get_stats": self.run_past_session
} 
       
        
        

   
    def buildResponse(self, frontend_message:dict) ->SessionData :
            """build response from backend"""
            print("BUILD RESPONSE MESSAGE:", frontend_message)
            print("KEYS:", frontend_message.keys())
            action = frontend_message["action"]
            content = frontend_message["content"]
            print("Content on system ", content)
            print("Action on system ", action)
            #FrontEnd -> BackEnd
            try:
                response: dict = self.features[action]
                return response(action,content)
            except:
                 #Raise some sort of exception such that the system knows that the user is giving invalid input
                 return self.test_dict

    #BackEnd -> Frontend  
    def send_requests_to_frontend(self, message: dict) -> SessionData:
        return self.backend_requests.build_responses(message)
        
        
    def run_user_session(self,action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        user_session:dict = self.user_session_manager.user_session_manager(action, content, self.data_manager)
        return user_session

        
    def run_settings(self, action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        return self.test_dict

    def run_past_session(self, action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        return self.test_dict




    def get_user_session_info()-> dict[str: IUserSessionManager]: 
        pass
    


"""

# get_settings
{
    "action": "get_settings",
    "content": {
        "defaultMinutes": 45,
        "breakReminders": True,
        "sounds": True,
        "strictMode": False
    }
}
# update_settings
{
    "action": "update_settings",
    "content": {}
}
# get_blocklist
{
    "action": "get_blocklist",
    "content": {
        "sites": []
    }
}
# update_blocklist
{
    "action": "update_blocklist",
    "content": {}
}
# get_session_summary
{
    "action": "get_session_summary",
    "content": {
        "focusedSeconds": 2700,
        "tabsBlocked": 12,
        "driftCount": 3,
        "score": 88,
        "longestStreakMin": 31
    }
}
{ 
    "action": "get_sessions",
    "content": [ -> content must be a lst not dict
        {
            "id": "session-1",
            "topic": "Math",
            "minutes": 45,
            "score": 92
        },
        {
            "id": "session-2",
            "topic": "C++",
            "minutes": 60,
            "score": 85
        }
    ]
}




"""