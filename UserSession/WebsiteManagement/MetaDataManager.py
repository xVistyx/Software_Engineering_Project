from .TabTimer import TabTimerHandler

from .AISessionEval import AISessionEval
from .OpenTab import OpenTabHandler
from .TabActivity import TabActivityHandler
from .CloseTab import ClosedTabHandler
from .DirtyTabs import DirtyTabHandler


"""
Things to add:
    - interfaces for the self.tabs dirty tabs 
    Add an interface for ActiveSessionConstructor
"""

class ActiveSessionConstructor:
    def __init__(self):
        self.ai_eval = AISessionEval()
        # One record per physical Chrome tab.
        self.tabs = {}
        # Existing records that must be updated in the DB.
        self.dirty_tabs = {}
        self.timer = TabTimerHandler(self.tabs)
        self.dirty = DirtyTabHandler(self.dirty_tabs)
        self.closed_tab = ClosedTabHandler(self.timer, self.tabs, self.dirty)
        self.tab_activity = TabActivityHandler(self.timer, self.tabs, self.dirty_tabs, self.dirty)
        self.time_manager = TimeManager(self.tab_activity, self.timer)
        self.open_tab = OpenTabHandler(self.tabs, self.timer)




class WebsiteMetadataEvaluator:
    """
    NEED to add this later
    """

    def __init__(self):
        self.session = ActiveSessionConstructor()
        self.meta_data = None
        self.reason_lst_tabs = ["tab_closed","tab_activated","page_updated",]
        
        self.event_manager = EventManager(self.session.timer, self.session.closed_tab)

        self.tab_manager = TabManager(
            time_manager=self.session.time_manager,
            open_tab=self.session.open_tab,
            closed_tab=self.session.closed_tab,
            tabs=self.session.tabs,
            dirty_tabs=self.session.dirty_tabs,
            ai_eval=self.session.ai_eval,
        )
   

    def handle_event(self, content: dict, topic: str) -> bool:
        reason = content.get("reason")
        state = content.get("state")

        if reason in self.reason_lst_tabs:
            is_new, metadata = self.tab_manager.handle_tab_state(reason, state, content, topic)
        else:
            is_new, metadata = self.event_manager.handle_event(reason, content, state)
        self.meta_data = metadata
        
        return is_new

  

    
    def get_website_meta_data(self) -> dict | None:
       

        if self.meta_data is None:
            return None

        result = self.meta_data.copy()

        result["time_spent"] = (self.session.timer.get_time_spent(result["tab_id"]))
        return result

    def get_dirty_tabs(self) -> list:
        """
        Returns changed existing records and clears the queue.

        These should be UPDATED in the DB by tab_id,
        not appended.
        """

        updates = list(self.session.dirty_tabs.values())

        self.session.dirty_tabs.clear()

        return updates



class EventManager:
    def __init__(self, timer, closed_tab):
        self.timer = timer
        self.closed_tab = closed_tab
       

    def handle_event(self, reason, content, state) -> tuple[bool, dict| None]:
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
        return self.closed_tab.deactivate_tab(tab_id)


class TabManager:
    def __init__(self,time_manager, open_tab, closed_tab, tabs, dirty_tabs, ai_eval):
        self.time_manager = time_manager
        self.open_tab = open_tab
        self.closed_tab =  closed_tab
        self.tabs = tabs
        self.dirty_tabs = dirty_tabs

        self.ai_eval = ai_eval
       
    def handle_tab_state(self, reason, state, content, topic) -> tuple[bool, dict| None]:
        if reason == "tab_closed":
            return self.close_tab_setter(content)
        
        tab_id = content.get("tab_id")
        if tab_id is None:
            return False, None
        if tab_id not in self.tabs:
            new_tab, meta_data =  self.create_tab(content, topic, tab_id)

        else:
            new_tab, meta_data = self.update_tab(content, topic, tab_id)
       
        self.time_manager.time_manager(reason, tab_id, state)
        

        return new_tab, meta_data



    def close_tab_setter(self, content) -> tuple[bool, dict |None ]:
        tab_id = content.get("tab_id")
        if tab_id is  None:
            return False, None
        
        closed, metadata = self.closed_tab.close_tab(tab_id, self.tabs, self.dirty_tabs)   
        return False, metadata if closed else None

    

    def create_tab(self, content, topic, tab_id) -> tuple[bool, dict | None]:
        metadata = self.open_tab.create_metadata(content,topic)
        self._is_related(metadata,topic)
        self.tabs[tab_id] = metadata
        new_tab = True
        print("NEW TAB:",tab_id)
        return new_tab, metadata

    def update_tab(self, content, topic, tab_id) -> tuple[bool, dict | None]:
        metadata = self.tabs[tab_id]
        self.open_tab.update_metadata(metadata,content,topic)
        self._is_related(metadata, topic)
        new_tab = False
        print("UPDATED TAB:",tab_id)
        return new_tab, metadata

    def _is_related(self, metadata, topic):
        """I can change this too a bool later so it will immidiatly stop if the website is not related"""
        metadata["is_related"] = (self.ai_eval.is_session_related(metadata,topic))


    

class TimeManager:
    def __init__(self, tab_activity, timer):
        self.tab_activity = tab_activity
        self.timer = timer

    def time_manager(self, reason, tab_id, state):
        if reason == "tab_activated":
            return self.tab_activity.activate_tab(tab_id)

        if (reason == "page_updated" and state == "active" and not self.timer.is_active(tab_id)):
            return self.tab_activity.activate_tab(tab_id)

        return False