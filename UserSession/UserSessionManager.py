from interfaces import IUserSessionManager, IDataManger
from .SessionStart import SessionStart
from .UserSessionDataManager import UserSessionDataManager
from datetime import datetime, timedelta

class UserSessionManager(IUserSessionManager):
    def __init__(self):
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}
        self.active_session = None
        self.session_start = SessionStart()# -> add interface to this
        self.user_session_data_manager = UserSessionDataManager()# -> add interface to this
    
    
        
    def user_session_manager(self, action:str, content:dict, data_manager:IDataManger) -> dict:
        self.user_session_data_manager.set_global_data_manager(data_manager)
        if action == "get_active_session":
            return self.get_active_session()
        elif action == "start_session":
            return self.start_user_session(content)
        elif action == "update_session":
            return self.update_user_session(content)
        elif action == "end_session":
            return self.end_user_session(content)

        else:
            return {
                "action": action,
                "content": {
                    "error": "Unknown user session action"
                }
            }



    def start_user_session(self, content:dict,) -> dict:
        """This functions main purpose is to log a new session such that the start gets logged in the db"""
        session_start:dict = self.session_start.session_start_as_dict(content)
        self.active_session = session_start
        print("Active session ", self.active_session)
        self.user_session_data_manager.log_session_start(session_start)
        return {
        "action": "start_session",
        "content": session_start
    }
          

    def get_active_session(self) -> dict:

        if self.active_session is None:
            print("YES")
            return {
                "action": "get_active_session",
                "content": {
                    "is_running": False
                }
            }
        #here need to calculate all the relivant information such that
        print("THERE IS AN ACTIVE SESSION")
        return self.updated_session_state()

    def updated_session_state(self):
        current_time = datetime.now()

        last_update = self.active_session["last_update_time"]

        time_spent = current_time - last_update
        seconds_spent = int(time_spent.total_seconds())

        self.active_session["time"] -= seconds_spent

        self.active_session["time"] = max(
            0,
            self.active_session["time"]
        )

        # save the timestamp we just updated at
        self.active_session["last_update_time"] = current_time

        return {
            "action": "get_active_session",
            "content": self.active_session
        }

    
    def update_user_session(self, content:dict ):
        """I dont yet know what this one does but its linked to the front end """
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