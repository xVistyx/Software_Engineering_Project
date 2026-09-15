from .TabTimer import TabTimerHandler

from .SessionInterfaces import  IWebsiteMetadataEvaluator, IDirtyTabsStore, ITabsStore, ITabTimerHandler, ITabActivityHandler
from .TabHandlers import InMemoryTabsStore
from ..AIEval.AISessionEval import AISessionEval
from .TabActivity import TabActivityHandler
from .TabHandlers import DirtyTabHandler


"""
Things to add:
    - interfaces for the self.tabs dirty tabs 
    Add an interface for ActiveSessionConstructor
"""



class ActiveSessionConstructor:
    def __init__(self):
        
        # One record per physical Chrome tab.
        self.tabs:ITabsStore = InMemoryTabsStore()
        # Existing records that must be updated in the DB.
        self.dirty_handler: IDirtyTabsStore = DirtyTabHandler()
        self.timer:ITabTimerHandler = TabTimerHandler(self.tabs)
        self.tab_activity: ITabActivityHandler = TabActivityHandler(self.timer, self.tabs, self.dirty_handler)


class WebsiteMetadataEvaluator(IWebsiteMetadataEvaluator):
    """
    NEED to add this later
    """

    def __init__(self):
        self.session = ActiveSessionConstructor()
        
        self.meta_data = None
        
        self.reason_lst_tabs = ["tab_closed","tab_activated","page_updated"]
        
        self.event_manager = EventManager(self.session.timer, self.session.tab_activity)

        self.tab_manager = TabManager(
            timer = self.session.timer,
            tab_activity = self.session.tab_activity,
            tabs = self.session.tabs,
        )
   

    def handle_event(self, content: dict, topic: str) -> bool:
        reason = content.get("reason")
        state = content.get("state")

        if reason in self.reason_lst_tabs:
            is_new, metadata = self.tab_manager.handle_tab_state(reason, state, content, topic)
        else:
            is_new, metadata = self.event_manager.handle_event(reason, state)
        self.meta_data = metadata
        
        return is_new

  

    
    def get_website_meta_data(self) -> dict | None:
       
        if self.meta_data is None:
            return None
        result = self.meta_data.copy()
        result["time_spent"] = (self.session.timer.get_time_spent(result["tab_id"]))
        return result

    def get_dirty_tabs(self) -> list[dict]:
        return self.session.dirty_handler.get_dirty_tabs()

    def snapshot_metadata(self, stop=False):
        if stop:
            self.event_manager.browser_unfocused()
        changes = {item['tab_id']: item for item in self.get_dirty_tabs()}
        active_id = self.session.timer.active_tab_id
        if active_id is not None:
            item = self.session.tabs.get_tab(active_id).copy()
            item['time_spent'] = self.session.timer.get_time_spent(active_id)
            changes[active_id] = item
        return list(changes.values())
    



class EventManager:
    def __init__(self, timer, tab_activity):
        self.timer:ITabTimerHandler = timer
        self.tab_activity:ITabActivityHandler = tab_activity
       

    def handle_event(self, reason: str, state: str) -> tuple[bool, dict| None]:
        if (reason == "window_focus_changed" and state == "unfocused"):
            bools,meta_data = self.browser_unfocused()
            if bools == True:
                return True, meta_data
            return False, None
            

        if (reason == "idle_state_changed" and state in {"idle", "locked"}):
            bools,meta_data = self.browser_unfocused()
            if bools == True:
                return True, meta_data
            return False, None

        if reason == "heartbeat":
            return False, None
       
        return False, None

    def browser_unfocused(self) -> tuple[bool, dict | None]:
        
        tab_id = self.timer.active_tab_id
        

        if tab_id is None:
            return False, None

        print("BROWSER UNFOCUSED")
        return self.tab_activity.deactivate_tab(tab_id)



class TabManager:
    def __init__(self,timer, tab_activity, tabs):
        self.timer: ITabTimerHandler = timer
       
        self.tab_activity:ITabActivityHandler = tab_activity
        self.tabs: ITabsStore  = tabs

    def handle_tab_state(self, reason, state, content, topic) -> tuple[bool, dict| None]:
        
        if reason == "tab_closed":
            return self.close_tab(content)
        
        tab_id = content.get("tab_id")
        if tab_id is None:
            return False, None

      
        
        if not self.tabs.contains(tab_id):
            new_tab, meta_data =  self.create_tab(content, topic, tab_id)
            

        else:
            new_tab, meta_data = self.update_tab(content, topic, tab_id)

        self.tabs.save_tab(tab_id, meta_data)
        self.time_manager(reason, tab_id, state)
        return new_tab, meta_data



    def close_tab(self, content) -> tuple[bool, dict |None ]:
        tab_id = content.get("tab_id")
        if tab_id is  None:
            return False, None
        closed, metadata = self.tab_activity.close_tab(tab_id)   
        return False, metadata if closed else None

    

    def create_tab(self, content, topic, tab_id) -> tuple[bool, dict | None]:
        metadata = self.tab_activity.create_metadata(content)
        metadata.setdefault("is_related", True)
        new_tab = True
        print("NEW TAB:",tab_id)
        return new_tab, metadata

    def update_tab(self, content, topic, tab_id) -> tuple[bool, dict | None]:
        metadata = self.tabs.get_tab(tab_id)
        metadata.setdefault("is_related", True)
        if metadata is None:
            return False, None
        self.tab_activity.update_metadata(metadata,content)
        new_tab = False
        print("UPDATED TAB:",tab_id)
        return new_tab, metadata


    def time_manager(self, reason, tab_id, state) -> bool:
            if reason == "tab_activated":
                return self.tab_activity.activate_tab(tab_id)
    
            if (reason == "page_updated" and state == "active" and not self.timer.is_active(tab_id)):
                return self.tab_activity.activate_tab(tab_id)
    
            return False
