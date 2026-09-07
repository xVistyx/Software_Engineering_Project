from dataclasses import dataclass, asdict


@dataclass
class WebsiteMetadata:
    tab_id: int
    title: str
    url: str
    favicon: str
    timestamp: str
    block: bool


class WebsiteMetadataManager:

    def __init__(self):
        pass
        

    def get_meta_data(self):
        pass

    def store_metadata(self, content: dict, session_data_manager) -> dict:

        metadata = WebsiteMetadata(
            tab_id=content["tab_id"],
            title=content["title"],
            url=content["url"],
            favicon=content["favicon"],
            timestamp=content["timestamp"]
        )

        metadata_dict = asdict(metadata)

        session_data_manager.set_meta_data(
            "website_metadata",
            metadata_dict
        )

        return {
            "stored": True
        }