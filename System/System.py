from interfaces import ISystem, IServerManage, IUserSessionCoordinator, IUserSessionCoordinator, ISettings, IPastSessionManager
from .BackendRequests import BackendRequests, SessionData, FrontEndSessionData 
from UserSession.UserSessionManager import UserSessionCoordinator
#from UserSession.UserSessionDataManager import UserSessionDataManager
from Settings.Settings import Settings
#from PastSessions.PastSessionManager import PastSessionManager
from DataBase.DataBaseManager import DataManager


class System(ISystem):
    def __init__(self):
       
        self.server_manager:IServerManage = None
        self.data_manager = DataManager() #Add type hint later
        self.backend_requests: BackendRequests = BackendRequests()
        self.frontend_message: FrontEndSessionData = {}
        self.user_session_manager: IUserSessionCoordinator = UserSessionCoordinator()
        self.settings:ISettings = Settings()
        self.is_session_active = False
        
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}
        
        self.features = {"start_session": self.run_user_session, "update_session": self.run_user_session, "end_session": self.run_user_session, "get_active_session": self.run_user_session,
                         "get_settings": self.run_settings, "update_settings": self.run_settings, "get_blocklist": self.run_settings,
                         "update_blocklist": self.run_settings,"get_session_summary": self.run_past_session,"get_sessions": self.run_past_session,
                          "get_stats": self.run_past_session, "log_meta_data": self.run_user_session
} 
       
        
        

   
    def buildResponse(self, frontend_message:dict) ->SessionData :
            """build response from backend"""
            #print("BUILD RESPONSE MESSAGE:", frontend_message)
            #print("KEYS:", frontend_message.keys())
            action = frontend_message["action"]
            content = frontend_message["content"]
            print("frontend message ", frontend_message)
            
            #print("Content on system ", content)
            #print("Action on system ", action)
            #FrontEnd -> BackEnd
            try:
                response: dict = self.features[action]
                
                print("RESPONSE: ", response)
                return response(action,content)
            except:
                 #Raise some sort of exception such that the system knows that the user is giving invalid input
                 return self.test_dict

    #BackEnd -> Frontend  

    def send_requests_to_frontend(self, message: dict) -> SessionData:
        return self.backend_requests.build_responses(message)
        
        
    def run_user_session(self,action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        """
         A user session has three states:
         - New session
         - running session
         - No session
        At the end add a way to get the session summary and store it in the db somehow -> this will still need
        to be implemented later. There is no direct connection to the UserSession Outside of this function
        """
        user_session:dict = self.user_session_manager.user_session_manager(action, content )
        print("USER SESSION ", user_session)
        print("ACTION", action)
        if action == "end_session":
            print("ENDING SESSION \n \n")
            self.send_to_db_manager( self.user_session_manager.send_to_global_db_manager())
            return user_session

        self.is_session_active = user_session['content']['is_running']
        print(self.is_session_active)
        
            

        return user_session


    def send_to_db_manager(self, data):
        """WICTOR this is ur function to send to ur backend IT contains the session summary"""

        pass
    def run_website_metadata(self, message: dict):

        return self.user_session_manager.block_website(
            message["content"]
        )
    
    def run_settings(self, action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        return self.test_dict

    def run_past_session(self, action:str, content: dict) -> dict:
         # must return a dictionary formated: action: str  content: dict
        """
         This function is reponsible for sending DB information to the frontend to load it.
         
        """
        return self.test_dict




   

