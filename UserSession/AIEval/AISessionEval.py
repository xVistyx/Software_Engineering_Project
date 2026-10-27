
class AISessionEval:
    def __init__(self):
        ...
    def is_session_related(self,meta_data: dict,topic: str) -> bool:
        """
        Placeholder until AI evaluation is implemented.
        Information looks something like this
        {
    "event_id": "...",
    "session_id": "...",
    "timestamp": "...",
    "state": "active",
    "reason": "page_updated",
    "tab_id": 66848747,
    "window_id": ...,

    "url": "https://www.bbc.com/news/...",
    "title": "Turnout so far highest on record as Israelis vote in pivotal election",

    "description": "The elections - the first since the Hamas-led attacks on Israel...",

    "favicon": "...",
    "audible": False,
    "pinned": False
}
        """
        
        return False
    
    def AI_meta_data_eval(self,meta_data: dict ,topic: str) -> bool:
        pass

"""
NEED TO FIX:
- For some reason AI blocking call is overwritten somewhere else meaning i have to figure out where. IT should be the only place that should be able
control the blocking.


"""