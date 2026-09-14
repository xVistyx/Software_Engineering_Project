from typing import Any

from .SessionInterfaces import IDirtyTabsStore, ITabsStore


class DirtyTabHandler(IDirtyTabsStore):
    def __init__(self, dirty_tabs: dict[int, dict[str, Any]] | None = None):
        self._dirty_tabs = dirty_tabs if dirty_tabs is not None else {}

    def mark_dirty(self, metadata: dict[str, Any]) -> None:
        """Queue an existing tab for a database update."""
        tab_id = metadata.get("tab_id")

        if tab_id is None:
            raise ValueError("Metadata must contain 'tab_id'")

        self._dirty_tabs[tab_id] = metadata.copy()

    def get_dirty_tabs(self) -> list[dict[str, Any]]:
        """Return queued updates and clear the queue."""
        updates = list(self._dirty_tabs.values())
        self._dirty_tabs.clear()
        return updates

class InMemoryTabsStore(ITabsStore):
    def __init__(self):
        self._tabs: dict[int, dict[str, Any]] = {}

    def get_tab(self, tab_id: int) -> dict[str, Any] | None:
        return self._tabs.get(tab_id)

    def save_tab(self,tab_id: int,metadata: dict[str, Any]) -> None:
        self._tabs[tab_id] = metadata

    def remove_tab(self, tab_id: int) -> dict[str, Any] | None:
        return self._tabs.pop(tab_id, None)

    def contains(self, tab_id: int) -> bool:
        return tab_id in self._tabs