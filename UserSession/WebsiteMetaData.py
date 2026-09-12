from dataclasses import dataclass, asdict
from datetime import datetime
from time import monotonic


@dataclass
class WebsiteMetadata:
    tab_id: int
    title: str
    url: str
    favicon: str
    timestamp: str
    block: bool
    currently_open: bool
    currently_active: bool
    time_spent: float
    is_related: bool


class TabTimer:
    """
    Responsible only for timing the currently active tab.
    """

    def __init__(self):
        self.active_tab_id = None
        self.started_at = None

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


class WebsiteMetadataManager:
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
    """

    def __init__(self):
        self.meta_data = None

        # One record per physical Chrome tab.
        self.tabs = {}

        self.timer = TabTimer()

        # Existing records that must be updated in the DB.
        self.dirty_tabs = {}

        self.new_tab = False

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
                self.close_tab(tab_id)

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
            metadata = self.create_metadata(content,topic)

            self.tabs[tab_id] = metadata
            self.meta_data = metadata
            self.new_tab = True

            print("NEW TAB:",tab_id
            )

        # ====================================================
        # EXISTING TAB
        # ====================================================

        else:
            metadata = self.tabs[tab_id]

            self.update_metadata(
                metadata,
                content,
                topic
            )

            self.meta_data = metadata
            self.new_tab = False

            print(
                "UPDATED TAB:",
                tab_id
            )

        # ====================================================
        # TIMER START
        # ====================================================

        # Most reliable event.
        if reason == "tab_activated":
            self.activate_tab(tab_id)

        # Important fallback:
        # Chrome can activate a tab while it is still
        # chrome://newtab, so the first valid HTTP event can
        # arrive as page_updated.
        elif (
            reason == "page_updated"
            and state == "active"
            and not self.timer.is_active(tab_id)
        ):
            self.activate_tab(tab_id)

        return self.new_tab

    # ========================================================
    # CREATE METADATA
    # ========================================================

    def create_metadata(
        self,
        content: dict,
        topic: str
    ) -> dict:

        metadata = WebsiteMetadata(
            tab_id=content["tab_id"],
            title=content.get("title", ""),
            url=content.get("url", ""),
            favicon=content.get("favicon", ""),
            timestamp=content.get(
                "timestamp",
                datetime.now().isoformat()
            ),
            block=False,
            currently_open=True,
            currently_active=False,
            time_spent=0.0,
            is_related=False
        )

        result = asdict(metadata)

        result["is_related"] = (
            self.is_session_related(
                result,
                topic
            )
        )

        return result

    # ========================================================
    # UPDATE EXISTING TAB
    # ========================================================

    def update_metadata(
        self,
        metadata: dict,
        content: dict,
        topic: str
    ) -> None:
        """
        Updates metadata only.
        Does not restart or stop the timer.
        """

        if content.get("title"):
            metadata["title"] = content["title"]

        if content.get("url"):
            metadata["url"] = content["url"]

        if content.get("favicon"):
            metadata["favicon"] = content["favicon"]

        metadata["currently_open"] = True

        metadata["is_related"] = (
            self.is_session_related(
                metadata,
                topic
            )
        )

    # ========================================================
    # ACTIVATE TAB
    # ========================================================

    def activate_tab(
        self,
        tab_id: int
    ) -> bool:

        if tab_id not in self.tabs:
            return False

        # Same tab is already being timed.
        if self.timer.is_active(tab_id):
            return False

        previous_tab_id, elapsed = (
            self.timer.start(tab_id)
        )

        # ====================================================
        # PREVIOUS TAB BECOMES INACTIVE
        # ====================================================

        if previous_tab_id is not None:
            previous_tab = self.tabs.get(
                previous_tab_id
            )

            if previous_tab is not None:
                previous_tab["time_spent"] += elapsed
                previous_tab["currently_active"] = False

                self.mark_dirty(
                    previous_tab
                )

                print(
                    "TAB INACTIVE:",
                    previous_tab_id,
                    "ADDED:",
                    round(elapsed, 2),
                    "TOTAL:",
                    round(
                        previous_tab["time_spent"],
                        2
                    )
                )

        # ====================================================
        # NEW ACTIVE TAB
        # ====================================================

        tab = self.tabs[tab_id]

        tab["currently_active"] = True
        tab["currently_open"] = True

        self.meta_data = tab

        self.mark_dirty(tab)

        print(
            "TAB ACTIVE:",
            tab_id
        )

        return True

    # ========================================================
    # DEACTIVATE TAB
    # ========================================================

    def deactivate_tab(
        self,
        tab_id: int
    ) -> bool:

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

        self.meta_data = tab

        self.mark_dirty(tab)

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

        return True

    # ========================================================
    # CLOSE TAB
    # ========================================================

    def close_tab(
        self,
        tab_id: int
    ) -> bool:

        tab = self.tabs.get(
            tab_id
        )

        if tab is None:
            return False

        if self.timer.is_active(tab_id):
            self.deactivate_tab(tab_id)

        tab["currently_open"] = False
        tab["currently_active"] = False

        self.meta_data = tab

        self.mark_dirty(tab)

        print(
            "TAB CLOSED:",
            tab_id,
            "FINAL TIME:",
            round(
                tab["time_spent"],
                2
            )
        )

        return True

    # ========================================================
    # BROWSER UNFOCUSED
    # ========================================================

    def browser_unfocused(self) -> bool:

        tab_id = self.timer.active_tab_id

        if tab_id is None:
            return False

        print(
            "BROWSER UNFOCUSED"
        )

        return self.deactivate_tab(
            tab_id
        )

    # ========================================================
    # DIRTY TAB TRACKING
    # ========================================================

    def mark_dirty(
        self,
        metadata: dict
    ) -> None:
        """
        Marks an existing tab as needing a DB update.
        """

        self.dirty_tabs[
            metadata["tab_id"]
        ] = metadata.copy()

    def get_dirty_tabs(
        self
    ) -> list:
        """
        Returns changed existing records and clears the queue.

        These should be UPDATED in the DB by tab_id,
        not appended.
        """

        updates = list(
            self.dirty_tabs.values()
        )

        self.dirty_tabs.clear()

        return updates

    # ========================================================
    # LIVE TIME
    # ========================================================

    def get_time_spent(
        self,
        tab_id: int
    ) -> float:

        tab = self.tabs.get(
            tab_id
        )

        if tab is None:
            return 0.0

        total = tab["time_spent"]

        total += self.timer.get_live_time(
            tab_id
        )

        return total

    # ========================================================
    # GET CURRENT METADATA
    # ========================================================

    def get_website_meta_data(self) -> dict | None:

        if self.meta_data is None:
            return None

        result = self.meta_data.copy()

        result["time_spent"] = (
            self.get_time_spent(
                result["tab_id"]
            )
        )

        return result

    # ========================================================
    # GET ALL TABS
    # ========================================================

    def get_all_website_meta_data(
        self
    ) -> list:

        result = []

        for tab_id, metadata in self.tabs.items():
            item = metadata.copy()

            item["time_spent"] = (
                self.get_time_spent(
                    tab_id
                )
            )

            result.append(item)

        return result

    # ========================================================
    # SESSION RELATED
    # ========================================================

    def is_session_related(self,meta_data: dict,topic: str) -> bool:
        """
        Placeholder until AI evaluation is implemented.
        """

        return True

    # ========================================================
    # AI
    # ========================================================

    def AI_meta_data_eval(self,meta_data: dict ,topic: str) -> bool:
        pass