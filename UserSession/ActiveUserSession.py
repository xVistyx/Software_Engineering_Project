from datetime import datetime
from typing import Any

from .SessionStart import SessionInfo
#from .WebsiteMetaData import WebsiteMetadataManager

from .MetadataProcessing.SessionInterfaces import IWebsiteMetadataEvaluator
class ActiveUserSessionManager:
    def __init__(self, website_meta_data, ai_eval):
        """Need to figure out the blocking of websites and information that isnt relivant"""
        
        self.website_meta_data: IWebsiteMetadataEvaluator = website_meta_data
        self.ai_eval = ai_eval #add an interface to this in the future

    def active_session_manager(self,metadata: dict,session_topic: str) -> tuple[dict | list[dict] | None, bool]:

        final_metadata, is_stored = self.webiste_data(metadata=metadata,session_topic=session_topic)

        if not is_stored:
            return {}, False
        
        if isinstance(final_metadata, list):

            for tab_metadata in final_metadata:
                tab_metadata["is_related"] = self._is_related(tab_metadata, session_topic)

      
        else:
            final_metadata["is_related"] = self._is_related(final_metadata,session_topic)

        return final_metadata, is_stored
         


        
        
    def updated_session_state(self, active_session: SessionInfo) -> dict[str, Any]:
            current_time = datetime.now()
    
            last_update = active_session["last_update_time"]
    
            time_spent = current_time - last_update
            seconds_spent = int(time_spent.total_seconds())
    
            active_session["time"] -= seconds_spent
    
            active_session["time"] = max(0,active_session["time"])
    
            # save the timestamp we just updated at
            active_session["last_update_time"] = current_time
            
            return {"action": "get_active_session",
                "content": active_session
            }
    
    
    def webiste_data(self, metadata: dict, session_topic:str, ) -> tuple[dict, bool]:
            is_new_tab = self.website_meta_data.handle_event(metadata,session_topic)
            stored = False
         
            if is_new_tab:
                print("NEW TAB -> STORE:",metadata.get("tab_id"))
                clean_metadata = (self.website_meta_data.get_website_meta_data()) 
                stored = True
                return [clean_metadata, stored]
            dirty_tabs = self.website_meta_data.get_dirty_tabs() 

            print("DIRTY TABS:", dirty_tabs)

            stored = len(dirty_tabs) > 0

            return [dirty_tabs, stored]

    def _is_related(self, metadata, topic) -> None:
        """I can change this too a bool later so it will immidiatly stop if the website is not related"""
        return self.ai_eval.is_session_related(metadata,topic)



    def block_website(self):
        """This function will call the blocking the blocking calls to stop a website form loading"""  
        ...
    
    
           
    

