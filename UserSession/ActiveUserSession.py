from datetime import datetime
from typing import Any
from .BlockingWebsites.WebsiteBlockerManager import BlockContent

from .SessionStart import SessionInfo
#from .WebsiteMetaData import WebsiteMetadataManager

from .MetadataProcessing.DynamicMetaData import DynamicWebpageMetaData
from .MetadataProcessing.SessionInterfaces import IWebsiteMetadataEvaluator

class ActiveUserSessionManager:
    def __init__(self, website_meta_data, ai_eval, website_blocking_manager):
        """Need to figure out the blocking of websites and information that isnt relivant"""
        
        self.website_meta_data_evaluator: IWebsiteMetadataEvaluator = website_meta_data
        self.ai_eval = ai_eval #add an interface to this in the future
        self.website_blocking_manager = website_blocking_manager
        self.dynamic_webpage_meta_data = DynamicWebpageMetaData()
    
    def active_session_manager(self,metadata: dict,session_topic: str, command) -> tuple[dict | list[dict] | None, bool]:
        print("COMMMAND \n \n ", command, "\n \n")
        if command  == "log_dynamic_content" or metadata["reason"] == "log_meta_data":
            list_of_recommendation, primary_meta_data = self.dynamic_meta_data(metadata, session_topic) 
            if primary_meta_data == None:
                 primary_meta_data = metadata


        else:
            #reason': 'window_focus_changed 
            print("NORMAL CONTENT ")
            print("\n\n META DATA, ", metadata, "\n\n")
            if metadata["reason"] == 'page_updated':
                meta_datas, block_info_lst = self.website_blocking_manager.website_blocker_manager(metadata,session_topic)
                primary_meta_data = metadata
                list_of_recommendation = block_info_lst
            else:
                primary_meta_data = metadata
                list_of_recommendation = ["NIGGEr"]   
             
        # should check before this if the website should be blocked or not -> if it needs to be blocked it shouldnt be able to continue and instead should return a blocking call
        #should_block = self.block_website(primary_meta_data)
        # add reason based removal 'reason': 'heartbeat'
        #metadatas, message_to_frontend = self.website_blocking_manager.website_blocker_manager(primary_meta_data,session_topic)
        final_metadata, is_stored = self.webiste_data(metadata=primary_meta_data,session_topic=session_topic)
        print("\n LIST OF RECOMMENDATIONS, ", list_of_recommendation, "\n\n")
        print("\n \n  FINAL METADATA ", final_metadata, "\n \n")
        
        if not is_stored:
            print("\n \n FINAL METADATA But not stored ", final_metadata, "\n \n")
            return {}, False, list_of_recommendation
        
        
        return final_metadata, is_stored, list_of_recommendation
         

  
         


    def dynamic_meta_data(self, metadata, session_topic) -> tuple[list, dict]:
        """
        Split the metadata between primary content and the feature content
        """
        
        not_storable = metadata.get("recommended_content")
        meta_datas, block_info_lst = self.website_blocking_manager.website_blocker_manager(metadata,session_topic) # -> this does some processing to the data so it will will be a dict containing content id and if it should be blocked (bool)
        print("\n \n  Block list info ", block_info_lst, "\n \n")
        print("\n \n META DATA  \n \n ", meta_datas, "\n \n")
        primary = metadata.get("primary_content")
        if primary is None:
             print("\n \n META DATA IS SHITTY FORMAT \n \n ", metadata, "\n \n")
             return block_info_lst,None
        primary_metadata = {
            "tab_id": metadata.get("tab_id"),
            "title": primary.get("title"),
            "url": primary.get("url"),
            "favicon": "",
            "timestamp": None,
            "block": False,
            "currently_open": True,
            "currently_active": True,
            "time_spent": 0.0,
            "is_related": False
        }
        print("SHOULD BLOCK \n \n", block_info_lst, "\n \n")
        return block_info_lst, primary_metadata

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
             
             

    
    
    def webiste_data(self, metadata: dict, session_topic:str) -> tuple[dict, bool]:

            is_new_tab = self.website_meta_data_evaluator.handle_event(metadata,session_topic)

            stored = False
         
         
            if is_new_tab:
                print("NEW TAB -> STORE:",metadata.get("tab_id"))
                  
                clean_metadata = (self.website_meta_data_evaluator.get_website_meta_data()) 
                stored = True
                return [clean_metadata, stored]
            dirty_tabs = self.website_meta_data_evaluator.get_dirty_tabs() 

            print("DIRTY TABS:", dirty_tabs)

            stored = len(dirty_tabs) > 0

            return [dirty_tabs, stored]

  



    
    
    
           
    

"""
{
  "tab_id": 66843914,
  "session_id": "04931a1c-2c08-4777-8750-5c9503284b4b",
  "page_type": "youtube_watch",
  "primary_content": {
    "content_id": "LP9CQ8uGHeY",
    "source": "youtube",
    "content_type": "video",
    "title": "Hello Kitty’s Bow Chase | Hello Kitty and Friends Supercute Adventures S2 EP 10",
    "url": "https://www.youtube.com/watch?v=LP9CQ8uGHeY",
    "channel": "Hello Kitty and Friends"
  },

  "recommended_content": [
    {
      "content_id": "wncB6LwnV_k",
      "source": "youtube",
      "content_type": "video",
      "title": "Season 5 Top 5 Episodes | Hello Kitty and Friends Supercute Adventures",
      "url": "https://www.youtube.com/watch?v=wncB6LwnV_k",
      "channel": "Hello Kitty and Friends"
    },
    {
      "content_id": "IfQgdWxAxMw",
      "source": "youtube",
      "content_type": "video",
      "title": "Hello Kitty, Kuromi and My Melody on The Plane! DIYs for Dolls LOL OMG",
      "url": "https://www.youtube.com/watch?v=IfQgdWxAxMw",
      "channel": "LaLiLu World"
    },
    {
      "content_id": "LiaYDPRedWQ",
      "source": "youtube",
      "content_type": "video",
      "title": "Avril Lavigne - Hello Kitty (Official Video)",
      "url": "https://www.youtube.com/watch?v=LiaYDPRedWQ",
      "channel": "Avril Lavigne"
    }
  ]
}


"""