

class WebsiteBlockerManager:
    def __init__(self, ai_eval):
        self.ai_eval = ai_eval

    def website_blocker_manager(self, meta_data, topic):
        if isinstance(meta_data, list):
        
            for tab_metadata in meta_data:
                tab_metadata["is_related"] = self.get_ai_evaluation(tab_metadata,topic) 
         
        else:
            meta_data["is_related"] = self.get_ai_evaluation(meta_data,topic)
        return meta_data
        


    
    def confidence_to_bool(self, ai_confidence) ->bool:
        return True

    def get_ai_evaluation(self, metadata, topic) -> int:
        ai_confidence = self.ai_eval.is_session_related(metadata, topic)
        return self.confidence_to_bool(ai_confidence)
    