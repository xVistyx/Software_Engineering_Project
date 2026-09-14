
class TabActivityHandler:
    def __init__(self, timer, tabs, dirty_tabs, dirty):
        self.timer = timer
        self.tabs = tabs
        self.dirty_tabs = dirty_tabs
        self.dirty = dirty
    
        
    def activate_tab(self, tab_id: int) -> bool:
        if not self.tabs.contains(tab_id):
            return False

        # Same tab is already being timed.
        if self.timer.is_active(tab_id):
            return False

        previous_tab_id, elapsed = self.timer.start(tab_id)

        # ====================================================
        # PREVIOUS TAB BECOMES INACTIVE
        # ====================================================

        if previous_tab_id is not None:
            previous_tab = self.tabs.get_tab(previous_tab_id)

            if previous_tab is not None:
                previous_tab["time_spent"] += elapsed
                previous_tab["currently_active"] = False

                self.dirty.mark_dirty(previous_tab)

                print(
                    "TAB INACTIVE:",
                    previous_tab_id,
                    "ADDED:",
                    round(elapsed, 2),
                    "TOTAL:",
                    round(previous_tab["time_spent"], 2)
                )

        # ====================================================
        # NEW ACTIVE TAB
        # ====================================================

        tab = self.tabs.get_tab(tab_id)

        tab["currently_active"] = True
        tab["currently_open"] = True

        self.meta_data = tab

        self.dirty.mark_dirty(tab)

        print("TAB ACTIVE:", tab_id)

        return True
    
    def close_tab(self, tab_id: int) -> tuple[bool, dict | None]:
            tab = self.tabs.get_tab(tab_id)
    
            if tab is None:
                return False, None
    
            if self.timer.is_active(tab_id):
                self.deactivate_tab(tab_id)
    
            tab["currently_open"] = False
            tab["currently_active"] = False
    
            self.dirty.mark_dirty(tab)
            return True, tab




