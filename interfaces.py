from abc import ABC, abstractmethod

class IUserSessionManager(ABC):
    @abstractmethod
    def setup_session() -> bool:
            pass


class ISystem(ABC):
    @abstractmethod
    def fetch_requests_from_frontend() -> None:
        pass
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




