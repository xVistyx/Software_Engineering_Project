

class ClosedTabHandler:
    def __init__(self, timer, tabs, dirty):
        self.timer = timer
        self.tabs = tabs
        self.dirty = dirty
    
    def close_tab(self,tab_id: int) ->list[bool, dict]:
        tab = self.tabs.get(tab_id)

        if tab is None:
            return False

        if self.timer.is_active(tab_id):
            self.deactivate_tab(tab_id)

        tab["currently_open"] = False
        tab["currently_active"] = False

        meta_data = tab

        self.dirty.mark_dirty(tab)

        print("TAB CLOSED:",tab_id,"FINAL TIME:",round(tab["time_spent"],2))

        return [True,meta_data] 
    def deactivate_tab(self,tab_id: int) -> list[bool, dict]:
    
        if not self.timer.is_active(tab_id):
            return False

        stopped_tab_id, elapsed = (
            self.timer.stop()
        )

        if stopped_tab_id is None:
            return False

        tab = self.tabs.get(
            stopped_tab_id
        )

        if tab is None:
            return False

        tab["time_spent"] += elapsed
        tab["currently_active"] = False

        meta_data = tab

        self.dirty.mark_dirty(tab)

        print(
            "TAB INACTIVE:",
            stopped_tab_id,
            "ADDED:",
            round(elapsed, 2),
            "TOTAL:",
            round(
                tab["time_spent"],
                2
            )
        )

        return [True, meta_data]