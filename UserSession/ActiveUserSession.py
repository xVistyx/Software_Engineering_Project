from datetime import datetime, timedelta
#from .WebsiteMetaData import WebsiteMetadataManager
from .WebsiteManagement.MetaDataManager import WebsiteMetadataEvaluator
class ActiveUserSessionManager:
    def __init__(self):
        """Need to figure out the blocking of websites and information that isnt relivant"""
    
        self.website_meta_data = WebsiteMetadataEvaluator()
        print("it initis")
       
        
        
    def updated_session_state(self, active_session):
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
    
    
    def webiste_data(self, metadata: dict, session_topic:str) -> dict:
            print(type(self.website_meta_data))
            is_new_tab = self.website_meta_data.eval_metadata(metadata,session_topic)
            print("START")
            
    
            stored = False
    
            # ========================================================
            # NEW TAB
            # ========================================================
    
            if is_new_tab:
                print("NEW TAB -> STORE:",metadata.get("tab_id"))
                clean_metadata = (self.website_meta_data.get_website_meta_data()) 
                stored = True
                return [clean_metadata, stored]
                
    
            # ========================================================
            # EXISTING TABS THAT CHANGED
            # ========================================================

            dirty_tabs = self.website_meta_data.get_dirty_tabs() 

            print("DIRTY TABS:", dirty_tabs)

            stored = len(dirty_tabs) > 0

            return [dirty_tabs, stored]

    def block_website(self):
        """This function will call the blocking the blocking calls to stop a website form loading"""  
        ...
    
    
           
    

