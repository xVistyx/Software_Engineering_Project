from .TabTimer import TabTimerHandler

from .AISessionEval import AISessionEval
from .OpenTab import OpenTabHandler
from .TabActivity import TabActivityHandler
from .CloseTab import ClosedTabHandler
from .DirtyTabs import DirtyTabHandler




class WebsiteMetadataEvaluator:
    """
    Manages website metadata for one focus session.

    Rules:
    - One metadata record per tab_id.
    - page_updated changes metadata only.
    - A timer starts on tab_activated OR the first active page_updated.
    - Switching tabs stops the previous timer.
    - Closing a tab stops its timer.
    - Losing browser focus stops the active timer.
    - Changed existing tabs are exposed through get_dirty_tabs().


    This class is still doing too much and it shouldnt be handling this much information
    """

    def __init__(self):
        self.ai_eval = AISessionEval()
        
        self.meta_data = None

        # One record per physical Chrome tab.
        self.tabs = {}
        # Existing records that must be updated in the DB.
        self.dirty_tabs = {}
        self.new_tab = False
        self.reason_lst_tabs = ["tab_closed","tab_activated","page_updated",]
        

        self.dirty = DirtyTabHandler(self.dirty_tabs)
        self.timer = TabTimerHandler(self.tabs)
        self.open_tab = OpenTabHandler(self.tabs, self.timer)
        self.closed_tab = ClosedTabHandler(self.timer, self.tabs, self.dirty)
        self.event_manager = EventManager(self.timer, self.closed_tab)
        self.tab_activity = TabActivityHandler(self.timer, self.tabs, self.dirty_tabs, self.dirty)
        self.tab_manager = TabManager(self.closed_tab, self.tabs, self.dirty_tabs, self.new_tab, self.ai_eval, self.tab_activity, self.timer, self.open_tab)
    # ========================================================
    # MAIN ENTRY POINT
    # ========================================================

    def eval_metadata(self, content: dict, topic: str) -> bool:
        reason = content.get("reason")
        state = content.get("state")

        if reason in self.reason_lst_tabs:
            is_new, metadata = self.tab_manager.tab_state_manager(
                reason, state, content, topic
            )
            self.new_tab = is_new
            self.meta_data = metadata
            return is_new

        event_result = self.event_manager.event_manager(reason, content, state)

        if event_result is not None:
            _, metadata = event_result
            self.meta_data = metadata

        return False

    def get_website_meta_data(self) -> dict | None:
        
        if self.meta_data is None:
            return None

        result = self.meta_data.copy()

        result["time_spent"] = (self.timer.get_time_spent(result["tab_id"]))
        return result

    def get_dirty_tabs(self) -> list:
        """
        Returns changed existing records and clears the queue.

        These should be UPDATED in the DB by tab_id,
        not appended.
        """

        updates = list(self.dirty_tabs.values())

        self.dirty_tabs.clear()

        return updates




class EventManager:
    def __init__(self, timer, closed_tab):
        self.timer = timer
        self.closed_tab = closed_tab

    def event_manager(self, reason, content, state) -> bool:
        # ====================================================
        # BROWSER LOST FOCUS
        # ====================================================

        if (reason == "window_focus_changed" and state == "unfocused"):
            bools,meta_data = self.browser_unfocused()
            if bools == True:
                self.meta_data = meta_data
                return True
            return False
            

        if (reason == "idle_state_changed" and state in {"idle", "locked"}):
            bools,meta_data = self.browser_unfocused()
            if bools == True:
                self.meta_data = meta_data
                return True
            return False

        # ====================================================
        # HEARTBEAT
        # ====================================================

        if reason == "heartbeat":
            return False

        # ====================================================
        # EVENTS WITHOUT WEBSITE DATA
        # ====================================================

        if "tab_id" not in content or "url" not in content:
            return False


    def browser_unfocused(self) -> list[bool, dict | None]:
        
        tab_id = self.timer.active_tab_id
        

        if tab_id is None:
            return False, None

        print("BROWSER UNFOCUSED")
        return self.closed_tab.deactivate_tab(tab_id)





    


class TabManager:
    def __init__(self, closed, tabs, dirty_tabs, new_tab, ai_eval, tab_activity, timer, open_tab):
        self.time_manager = TimeManager(tab_activity, timer)
        self.closed = closed
        self.tabs = tabs
        self.dirty_tabs = dirty_tabs
        self.new_tab = new_tab
        self.ai_eval = ai_eval
        self.tab_activity = tab_activity
        self.open_tab = open_tab
        

    def tab_state_manager(self, reason, state, content, topic):
        if reason == "tab_closed":
            return self.close_tab_setter(content)
        
        tab_id = content["tab_id"]
        if tab_id is None:
            return False, None
        if tab_id not in self.tabs:
            self.new_tabs(content, topic, tab_id)

        else:
            self.existing_tab(content, topic, tab_id)
       
        self.time_manager.time_manager(reason, tab_id, state)

        return self.new_tab, self.meta_data



    def close_tab_setter(self, content) -> list[bool, dict]:
        tab_id = content.get("tab_id")
        if tab_id is  None:
            return False, None
        
        closed, metadata = self.closed.close_tab(tab_id, self.tabs, self.dirty_tabs)

        self.new_tab = False
        self.meta_data = metadata if closed else None
        return False, self.meta_data

    

    def new_tabs(self, content, topic, tab_id):
        metadata = self.open_tab.create_metadata(content,topic)
        self._is_related(metadata,topic)

        self.tabs[tab_id] = metadata
        self.meta_data = metadata
        self.new_tab = True

        print("NEW TAB:",tab_id)

    def existing_tab(self, content, topic, tab_id):
        metadata = self.tabs[tab_id]
        self.open_tab.update_metadata(metadata,content,topic)
        self._is_related(metadata, topic)
        self.meta_data = metadata
        self.new_tab = False
        print("UPDATED TAB:",tab_id)

    def _is_related(self, metadata, topic):
        metadata["is_related"] = (self.ai_eval.is_session_related(metadata,topic))
    





class TimeManager:
    def __init__(self, tab_activity, timer):
        self.tab_activity = tab_activity
        self.timer = timer

    def time_manager(self, reason, tab_id, state):
        if reason == "tab_activated":
            return self.tab_activity.activate_tab(tab_id)

        if (
            reason == "page_updated"
            and state == "active"
            and not self.timer.is_active(tab_id)
        ):
            return self.tab_activity.activate_tab(tab_id)

        return False