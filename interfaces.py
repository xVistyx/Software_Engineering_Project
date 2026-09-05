from abc import ABC, abstractmethod


class IUserSessionManager(ABC):
    pass

class ISystem(ABC):
  
    
    @abstractmethod
    def send_requests_to_frontend(message:str) -> None:
        pass

   
    
    @abstractmethod
    def get_user_session_info()-> dict[str: IUserSessionManager]: # add ISession here
        pass

class IServerManage(ABC):

    @abstractmethod
    def setup_ai() -> None:
        pass

    @abstractmethod
    def get_ai_response(message:str) -> dict[str, str]:
        pass




class ISettings(ABC):
    @abstractmethod
    def view_settings():
        pass

class IPastSessionManager(ABC):
    pass

class IDataManger(ABC):
    pass