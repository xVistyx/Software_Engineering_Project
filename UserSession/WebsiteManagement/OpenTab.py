from datetime import datetime
from dataclasses import dataclass
from dataclasses import  asdict

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

class OpenTabHandler:
    def __init__(self, timer, tabs):
        self.timer = timer
        self.tabs = tabs

    def create_metadata(self,content: dict,topic: str) -> dict:
    
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
    def update_metadata(self,metadata: dict,content: dict,topic: str) -> None:
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
   