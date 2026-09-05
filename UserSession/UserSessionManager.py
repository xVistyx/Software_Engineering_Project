from interfaces import IUserSessionManager, IDataManger
from .SessionStart import SessionStart
from .UserSessionDataManager import UserSessionDataManager
class UserSessionManager(IUserSessionManager):
    def __init__(self):
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}
        self.active_session = False
        self.session_start = SessionStart()# -> add interface to this
        self.user_session_data_manager = UserSessionDataManager()# -> add interface to this
    
    
        
    def user_session_manager(self, action:str, content:dict, data_manager: IDataManger ):
        
        if action == "start_session":
            return self.start_user_session(content, data_manager)
        elif action == "update_session":
            return self.update_user_session(content)
        else:
            return self.end_user_session(content)

    def start_user_session(self, content:dict, data_manger ) -> dict:
        """This functions main purpose is to log a new session such that the start gets logged in the db"""
        session_start:dict = self.session_start.session_start_as_dict(content)
        self.user_session_data_manager.log_session_start(session_start,data_manger)
        return {
        "action": "start_session",
        "content": session_start
    }
          



    def update_user_session(self, content:dict ):
        pass

    def end_user_session(self, content:dict ):
        pass


    def get_db_session_data(self):
        """This function will be responsible for getting information from the db about current session """
        pass
    def set_db_session_data(self):
            """This function will be responsible for writing information to the db about current session """
            pass
        


     

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