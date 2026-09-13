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
        self.dirty = DirtyTabHandler(self.dirty_tabs)
        self.timer = TabTimerHandler(self.tabs)
        self.open_tab = OpenTabHandler(self.tabs, self.timer)
        self.closed_tab = ClosedTabHandler(self.timer, self.tabs, self.dirty)
        self.tab_activity = TabActivityHandler(self.timer, self.tabs, self.dirty_tabs, self.dirty)
    # ========================================================
    # MAIN ENTRY POINT
    # ========================================================

    def eval_metadata(self, content: dict, topic: str) -> bool:
        print("Does it ever call this? \n \n \n")
        print("META CONTENT:", content)
        print("TOPIC:", topic)

        reason = content.get("reason")
        state = content.get("state")

        # ====================================================
        # TAB CLOSED
        # ====================================================

        if reason == "tab_closed":
            tab_id = content.get("tab_id")

            if tab_id is not None:
                bools,meta_data = self.closed_tab.close_tab(tab_id, self.tabs, self.dirty_tabs)
                if bools == True:
                    self.meta_data = meta_data

            return False

        # ====================================================
        # BROWSER LOST FOCUS
        # ====================================================

        if (reason == "window_focus_changed" and state == "unfocused"):
            self.browser_unfocused()
            return False

        # ====================================================
        # IDLE / LOCKED
        # ====================================================

        if (reason == "idle_state_changed" and state in {"idle", "locked"}):
            self.browser_unfocused()
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

        tab_id = content["tab_id"]

        # ====================================================
        # NEW TAB
        # ====================================================

        if tab_id not in self.tabs:
            metadata = self.open_tab.create_metadata(content,topic)
            self._is_related(metadata,topic)

            self.tabs[tab_id] = metadata
            self.meta_data = metadata
            self.new_tab = True

            print("NEW TAB:",tab_id)

        # ====================================================
        # EXISTING TAB
        # ====================================================

        else:
            metadata = self.tabs[tab_id]

            open_tab = self.open_tab.update_metadata(metadata,content,topic)
            self._is_related(open_tab, topic)
            self.meta_data = metadata
            self.new_tab = False
            print("UPDATED TAB:",tab_id)

        # ====================================================
        # TIMER START
        # ====================================================

        # Most reliable event.
        if reason == "tab_activated":
            self.tab_activity.activate_tab(tab_id)

        # Important fallback:
        # Chrome can activate a tab while it is still
        # chrome://newtab, so the first valid HTTP event can
        # arrive as page_updated.
        elif (reason == "page_updated"and state == "active" and not self.timer.is_active(tab_id)):
            self.tab_activity.activate_tab(tab_id)

        return self.new_tab


    def _is_related(self, metadata, topic):
        metadata["is_related"] = (self.ai_eval.is_session_related(metadata,topic))

    def browser_unfocused(self) -> bool:
    
        tab_id = self.timer.active_tab_id

        if tab_id is None:
            return False

        print("BROWSER UNFOCUSED")
        bools, meta_data = self.closed_tab.deactivate_tab(tab_id)
        if bools == True:
            self.meta_data = meta_data
        return bools

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
    
