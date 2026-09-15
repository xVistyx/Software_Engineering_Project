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

    @abstractmethod
    def snapshot_metadata(self, stop: bool = False) -> list[dict[str, Any]]:
        """Return current tab totals for a checkpoint or session completion."""
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
        raise NotImplementedError

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

class ITabActivityHandler(ABC):
    @abstractmethod
    def activate_tab(self, tab_id: int) -> bool:
        pass

    @abstractmethod
    def close_tab(self, tab_id: int) -> tuple[bool, dict | None]:
        pass

    @abstractmethod
    def create_metadata(self,content: dict) -> dict:
        pass

    @abstractmethod    
    def update_metadata(self,metadata: dict,content: dict) -> None:
        pass

    @abstractmethod       
    def get_all_website_meta_data(self) -> list:
        pass

class ITabManager(ABC):
    @abstractmethod
    def handle_tab_state(self, reason:str, state:str, content:dict, topic:str) -> tuple[bool, dict| None]:
        pass
    
    @abstractmethod
    def close_tab(self, content:dict) -> tuple[bool, dict |None ]:
        pass

    @abstractmethod
    def create_tab(self, content:dict, topic:str, tab_id:str) -> tuple[bool, dict | None]:
        pass

    @abstractmethod
    def update_tab(self, content:dict, topic:str, tab_id:str) -> tuple[bool, dict | None]:
        pass
    
    @abstractmethod
    def _is_related(self, metadata:dict, topic:str) -> None:
        pass

    @abstractmethod
    def time_manager(self, reason:str, tab_id, state:str) -> bool:
        pass

class IEventManager(ABC):
    @abstractmethod
    def handle_event(self, reason:str, content:dict, state:str) -> tuple[bool, dict| None]:
        pass
                
    @abstractmethod
    def browser_unfocused(self) -> tuple[bool, dict | None]:
        pass
