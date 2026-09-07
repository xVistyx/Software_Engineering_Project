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

    def store_metadata(self, content: dict) -> dict:

        print("META CONTENT:", content)

        metadata = WebsiteMetadata(
            tab_id=content["tab_id"],
            title=content["title"],
            url=content["url"],
            favicon=content["favicon"],
            timestamp=content["timestamp"],
            block=content.get("block", False)
        )

        metadata_dict = asdict(metadata)

        print("CLEAN METADATA:", metadata_dict)

        return metadata_dict