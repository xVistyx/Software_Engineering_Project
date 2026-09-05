from interfaces import IPastSessionManager

class PastSessionManager(IPastSessionManager):
    def __init__(self):
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}

    def past_session_manager(self, action: str, content: dict):
            if action == "get_sessions":
                return {
                     "action": action,
                    "content": []
                        }
            
            elif action == "get_stats":
                return {
                    "action": action,
                    "content": {
                            "total": 0,
                            "thisWeek": 0,
                            "focusedHours": 0,
                            "peakDriftHour": "-"
                                }
                        }
            
            elif action == "get_session_summary":
                            return {
                                "action": action,
                                "content": {
                                    "id": content.get("session_id"),
                                    "score": 0,
                                    "minutes": 0
                                }
                            }
            return self.test_dict
    
    
    def get_stats(self):
        pass
    def get_session_summary(self):
        pass
    def get_sessions(self):
        pass

"""
# get_session_summary
{
    "action": "get_session_summary",
    "content": {
        "focusedSeconds": 2700,
        "tabsBlocked": 12,
        "driftCount": 3,
        "score": 88,
        "longestStreakMin": 31
    }
}
{ 
    "action": "get_sessions",
    "content": [ -> content must be a lst not dict
        {
            "id": "session-1",
            "topic": "Math",
            "minutes": 45,
            "score": 92
        },
        {
            "id": "session-2",
            "topic": "C++",
            "minutes": 60,
            "score": 85
        }
    ]
}


"""
