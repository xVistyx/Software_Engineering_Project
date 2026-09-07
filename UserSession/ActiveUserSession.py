from datetime import datetime, timedelta

class ActiveUserSession:
    def __int__(self):
        """Need to figure out the blocking of websites and information that isnt relivant"""
        pass
    def updated_session_state(self, active_session):
            current_time = datetime.now()
    
            last_update = active_session["last_update_time"]
    
            time_spent = current_time - last_update
            seconds_spent = int(time_spent.total_seconds())
    
            active_session["time"] -= seconds_spent
    
            active_session["time"] = max(0,active_session["time"])
    
            # save the timestamp we just updated at
            active_session["last_update_time"] = current_time
    
            return {
                "action": "get_active_session",
                "content": active_session
            }
    
