from abc import ABC, abstractmethod



class ISystem(ABC):
  
    
    @abstractmethod
    def send_requests_to_frontend(message:str) -> None:
        pass

   
   

#OPTIONAL RN NOT USED
class IServerManage(ABC):

    @abstractmethod
    def setup_ai() -> None:
        pass

    @abstractmethod
    def get_ai_response(message:str) -> dict[str, str]:
        pass




class ISettings(ABC):
    @abstractmethod
    def settings_manager(self, action:str, content:dict):
        pass

class IPastSessionManager(ABC):
    pass
class IDataManger(ABC):
    pass



class IUserSessionCoordinator(ABC):

    @abstractmethod
    def user_session_manager(self, action:str, content:dict, data_manager) -> dict:
        pass

    @abstractmethod
    def start_user_session(self, content:dict) -> dict:
        pass

    @abstractmethod
    def get_active_session() -> dict:
        pass
   

    @abstractmethod
    def update_user_session(self, content:dict ):
        """I dont yet know what this one does but its linked to the front end """
        pass
    
    @abstractmethod
    def end_user_session(self, content:dict ):
        pass
    
    @abstractmethod
    def get_db_session_data(self):
        """This function will be responsible for getting information from the db about current session """
        pass

    @abstractmethod
    def set_db_session_data(self):
        """This function will be responsible for writing information to the db about current session """
        pass



    