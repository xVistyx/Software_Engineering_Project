class ClosedTabHandler:
    def __init__(self, timer, tabs, dirty):
        self.timer = timer
        self.tabs = tabs
        self.dirty = dirty

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