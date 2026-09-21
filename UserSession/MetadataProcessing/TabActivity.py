from datetime import datetime
from dataclasses import dataclass
from dataclasses import  asdict
from .SessionInterfaces import ITabsStore, IDirtyTabsStore, ITabActivityHandler, ITabTimerHandler

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


class TabActivityHandler(ITabActivityHandler):
    def __init__(self, timer, tabs, dirty_tabs):
        self.timer:ITabTimerHandler = timer
        self.tabs: ITabsStore = tabs
        self.dirty_tabs: IDirtyTabsStore = dirty_tabs
        
    
        
    def activate_tab(self, tab_id: int) -> bool:
        if not self.tabs.contains(tab_id):
            return False

        # Same tab is already being timed.
        if self.timer.is_active(tab_id):
            return False

        previous_tab_id, elapsed = self.timer.start(tab_id)

   

        if previous_tab_id is not None:
            previous_tab = self.tabs.get_tab(previous_tab_id)

            if previous_tab is not None:
                previous_tab["time_spent"] += elapsed
                previous_tab["currently_active"] = False

                self.dirty_tabs.mark_dirty(previous_tab)

                print(
                    "TAB INACTIVE:",
                    previous_tab_id,
                    "ADDED:",
                    round(elapsed, 2),
                    "TOTAL:",
                    round(previous_tab["time_spent"], 2)
                )

        tab = self.tabs.get_tab(tab_id)

        tab["currently_active"] = True
        tab["currently_open"] = True

        self.meta_data = tab

        self.dirty_tabs.mark_dirty(tab)

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

    def deactivate_tab(self, tab_id: int) -> tuple[bool, dict | None]:
        tab = self.tabs.get_tab(tab_id)
        # Tab doesn't exist
        if tab is None:
            return False, None
        # Tab isn't currently being timed
        if not self.timer.is_active(tab_id):
            tab["currently_active"] = False
            return False, tab
        # Stop timer and get elapsed active time
        elapsed_time = self.timer.stop(tab_id)[1]

        # Add this active period to total time spent
        tab["time_spent"] += elapsed_time
        tab["currently_active"] = False
        # Metadata changed, so mark it for saving/updating
        self.dirty_tabs.mark_dirty(tab)
        return True, tab

    def create_metadata(self,content: dict) -> dict:
        
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
        
                
        
                return result
    def update_metadata(self,metadata: dict,content: dict) -> None:
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
    
            return metadata
    
    
        
    def get_all_website_meta_data(self) -> list:
    
            result = []
    
            for tab_id, metadata in self.tabs.items():
                item = metadata.copy()
    
                item["time_spent"] = (
                    self.timer.get_time_spent(
                        tab_id
                    )
                )
    
                result.append(item)
    
            return result
    


