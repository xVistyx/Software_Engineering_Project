from interfaces import IUserSessionManager
from .SessionStart import SessionStart
from .UserSessionDataManager import UserSessionDataManager



from .ActiveUserSession import ActiveUserSession

class UserSessionManager(IUserSessionManager):
    def __init__(self):
        """I need to add threading to this to make it threading safe. This file shouldnt do anything but coordinate. Logic is handeled in the manager Files"""
        self.active_session = None
        self.session_start = SessionStart()# -> add interface to this
        self.user_session_data_manager = UserSessionDataManager()# -> add interface to this
        self.active_user_session = ActiveUserSession()# -> add interface to this
        
        
    
    
        
    def user_session_manager(self, action:str, content:dict, data_manager) -> dict:
        self.user_session_data_manager.set_global_data_manager(data_manager)
        
        if action == "get_active_session":
            return self.get_active_session()
        elif action == "start_session":
            return self.start_user_session(content)
        elif action == "update_session":
            return self.update_user_session(content, "update_session")
        elif action == "end_session":
            return self.end_user_session(content)
        elif action == "log_meta_data":
            return {
                "action": "log_meta_data",
                "content": self.update_user_session(content, "log_meta_data") # naming is a bit weird need to fix. But linked to frontend so cannot rn -> future this will be function call to block the websites
            }

        else:
            return {
                "action": action,
                "content": {
                    "error": "Unknown user session action"
                }
            }
    def start_user_session(self, content:dict) -> dict:
        """This functions main purpose is to log a new session such that the start gets logged in the db"""
        session_start:dict = self.session_start.session_start_as_dict(content)
        self.active_session = session_start
        print("Active session ", session_start)
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

        if command == "log_meta_data":
            topic = self.active_session["topic"]
            metadata_result, stored = (self.active_user_session.block_website(content,topic))
            if not stored:
                return
            if isinstance(metadata_result, dict):

                print("NEW TAB -> WRITING")
                self.user_session_data_manager.write_metadata_to_session_json(metadata_result)

            elif isinstance(metadata_result, list):

                for changed_tab in metadata_result:
                    self.user_session_data_manager.update_metadata_in_session_json(changed_tab)

        else:
            self.active_user_session.updated_session_state(content)
            


    def end_user_session(self, content:dict ):
        pass


    def get_db_session_data(self):
        """This function will be responsible for getting information from the db about current session """
        pass

    def set_db_session_data(self):
        """This function will be responsible for writing information to the db about current session """
        pass


"""
We still need a way to end the session
-> needs to clear the db etc to not make the software to intensive to run
"""        


     

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