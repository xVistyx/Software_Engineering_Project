from interfaces import IUserSessionManager
from .SessionStart import SessionStart
from .UserSessionDataManager import UserSessionDataManager
from .WebsiteMetaData import WebsiteMetadataManager


from .ActiveUserSession import ActiveUserSession

class UserSessionManager(IUserSessionManager):
    def __init__(self):
        #self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}
        self.active_session = None
        self.session_start = SessionStart()# -> add interface to this
        self.user_session_data_manager = UserSessionDataManager()# -> add interface to this
        self.active_user_session = ActiveUserSession()# -> add interface to this
        self.website_meta_data= WebsiteMetadataManager()# -> add interface to this
        
    
    
        
    def user_session_manager(self, action:str, content:dict, data_manager) -> dict:
        self.user_session_data_manager.set_global_data_manager(data_manager)
        
        if action == "get_active_session":
            return self.get_active_session()
        elif action == "start_session":
            return self.start_user_session(content)
        elif action == "update_session":
            return self.update_user_session(content)
        elif action == "end_session":
            return self.end_user_session(content)
        elif action == "log_meta_data":
            return {
                "action": "log_meta_data",
                "content": self.block_website(content) # naming is a bit weird need to fix. But linked to frontend so cannot rn -> future this will be function call to block the websites
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

        return {
        "action": "start_session",
        "content": session_start
        }

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
   




    def block_website(self, metadata: dict) -> dict:

        is_new_tab = self.website_meta_data.eval_metadata(
            metadata,
            self.active_session["topic"]
        )

        stored = False

        # ========================================================
        # NEW TAB
        # ========================================================

        if is_new_tab:

            print(
                "NEW TAB -> STORE:",
                metadata.get("tab_id")
            )

            clean_metadata = (
                self.website_meta_data
                .get_website_meta_data()
            )

            self.user_session_data_manager.write_metadata_to_session_json(
                clean_metadata
            )

            stored = True


        # ========================================================
        # EXISTING TABS THAT CHANGED
        # ========================================================

        dirty_tabs = (
            self.website_meta_data
            .get_dirty_tabs()
        )

        for changed_metadata in dirty_tabs:

            print(
                "UPDATE TAB:",
                changed_metadata["tab_id"],
                "TIME:",
                changed_metadata["time_spent"]
            )

            self.user_session_data_manager.update_metadata_in_session_json(
                changed_metadata
            )

            stored = True


        return {
            "stored": stored
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