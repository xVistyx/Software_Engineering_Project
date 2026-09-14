from abc import ABC, abstractmethod
from typing import Any

class IWebsiteMetadataEvaluator(ABC):
    @abstractmethod
    def handle_event(self,content: dict[str, Any],topic: str,) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_website_meta_data(self) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_dirty_tabs(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class ITabsStore(ABC):
    @abstractmethod
    def get_tab(self, tab_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def save_tab(self, tab_id: int, metadata: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_tab(self, tab_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def contains(self, tab_id: int) -> bool:
        raise NotImplementedError


class IDirtyTabsStore(ABC):
    @abstractmethod
    def mark_dirty(self, metadata: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_dirty_tabs(self) -> list[dict[str, Any]]:
        raise NotImplementedError

class ITabTimerHandler(ABC):
    @abstractmethod
    def is_active(self, tab_id: int) -> bool:
        pass
    @abstractmethod
    def start(self, tab_id: int) -> tuple[int | None, float]:
        pass
    @abstractmethod
    def stop(self) -> tuple[int | None, float]:
        pass
    @abstractmethod
    def get_live_time(self, tab_id: int) -> float:
        pass

    @abstractmethod
    def get_time_spent(self, tab_id: int) -> float:
        pass