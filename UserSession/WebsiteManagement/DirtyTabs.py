
class DirtyTabHandler:
    def __init__(self, dirty_dict):
          self.dirty_tab_dict = dirty_dict
    def mark_dirty(self,metadata: dict,) -> dict:
            """
            Marks an existing tab as needing a DB update.
            """
            self.dirty_tab_dict[metadata["tab_id"]] = metadata.copy()
            return self.dirty_tab_dict 
    
    