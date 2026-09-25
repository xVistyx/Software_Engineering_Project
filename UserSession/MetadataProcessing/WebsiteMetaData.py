from dataclasses import dataclass
@dataclass
class WebsiteMetadata:
    tab_id: int
    title: str
    url: str
    favicon: str
    timestamp: str
    block: bool | None
    currently_open: bool
    currently_active: bool
    time_spent: float
    is_related: bool | None