
from dataclasses import dataclass, asdict


@dataclass
class BlockContent:
    website_url: str
    content_id: str
    block: bool


class WebsiteBlockerManager:
    def __init__(self, ai_eval):
        self.ai_eval = ai_eval
    def website_blocker_manager(self, meta_datas, topic):
        block_content_list = []
        if "recommended_content" in meta_datas:
            meta_data = meta_datas["recommended_content"]
            for video in meta_data:
                is_related = self.get_ai_evaluation(
                    video, topic
                )

                video["is_related"] = is_related

                block = BlockContent(
                    website_url=video["url"],
                    content_id=video["content_id"],
                    block=not is_related
                )

                block_content_list.append(block)
        else:
            is_related = self.get_ai_evaluation(
                            meta_datas, topic
                        )

            meta_datas["is_related"] = is_related

            block = BlockContent(website_url=meta_datas["url"],
                content_id="",
                block=not is_related
            )

            block_content_list.append(block)


        response = {
            "tab_id": meta_datas.get("tab_id"),
            "blocking_decisions": [
                asdict(block)
                for block in block_content_list
            ]
        }

      

        return meta_datas, response

    def confidence_to_bool(self, ai_confidence) -> bool:
        return True

    def get_ai_evaluation(self, metadata, topic) -> bool:

        ai_confidence = self.ai_eval.is_session_related(
            metadata, topic
        )

        return self.confidence_to_bool(ai_confidence)
