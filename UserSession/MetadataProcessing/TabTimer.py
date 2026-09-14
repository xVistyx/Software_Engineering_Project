from time import monotonic
from .SessionInterfaces import ITabTimerHandler

class TabTimerHandler(ITabTimerHandler):
    """
    Responsible only for timing the currently active tab.
    """

    def __init__(self, tabs):
        self.active_tab_id:dict = None
        self.started_at: monotonic = None
        self.tabs:dict = tabs
       

    def is_active(self, tab_id: int) -> bool:
        return self.active_tab_id == tab_id

    def start(self, tab_id: int) -> tuple[int | None, float]:
        """
        Starts timing tab_id.

        If another tab was active, returns:
            previous_tab_id, elapsed_seconds

        If the same tab is already active, does nothing.
        """

        if self.active_tab_id == tab_id:
            return None, 0.0

        previous_tab_id = None
        elapsed = 0.0

        if self.active_tab_id is not None:
            previous_tab_id, elapsed = self.stop()

        self.active_tab_id = tab_id
        self.started_at = monotonic()

        return previous_tab_id, elapsed

    def stop(self) -> tuple[int | None, float]:
        if self.active_tab_id is None or self.started_at is None:
            return None, 0.0

        tab_id = self.active_tab_id
        elapsed = monotonic() - self.started_at

        self.active_tab_id = None
        self.started_at = None

        return tab_id, elapsed

    def get_live_time(self, tab_id: int) -> float:
        if self.active_tab_id != tab_id or self.started_at is None:
            return 0.0

        return monotonic() - self.started_at

    def get_time_spent(self, tab_id: int) -> float:

        tab = self.tabs.get_tab(tab_id)

        if tab is None:
            return 0.0

        total = tab["time_spent"]

        total += self.get_live_time(tab_id)

        return total
    
