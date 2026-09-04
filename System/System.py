from interfaces import ISystem, IServerManage, IUserSessionManager

from .BackendRequests import BackendRequests, SessionData, FrontEndSessionData  # Relative import



class System(ISystem):
    def __init__(self):
        #self.session_manager: IUserSessionManager = None
        self.server_manager:IServerManage = None
        self.backend_requests: BackendRequests = BackendRequests()
        self.frontend_message: FrontEndSessionData = {}
        self.test = {"action": "Send to frontend", "content": 32}

    def buildResponse(self) ->SessionData :
        """From this we build the response """
        pass

    #FrontEnd -> BackEnd
    def fetch_requests_from_frontend(self, message:dict) -> None:
         self.frontend_message: FrontEndSessionData = self.backend_requests.handle_requests(message)

    #BackEnd -> Frontend  
    def send_requests_to_frontend(self, message: dict) -> SessionData:
        return self.backend_requests.build_responses(message)
        
        
    
    def get_user_session_info()-> dict[str: IUserSessionManager]: 
        pass
    
