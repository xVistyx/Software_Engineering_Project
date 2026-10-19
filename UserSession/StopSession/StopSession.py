from datetime import datetime

from .GenerateSummary import GenerateSummary, SessionSummaryForDB

class StopSession:
    def __init__(self):
        
        self.session_summary = GenerateSummary()

    def manage_session_stop(self, session_data: dict, active_session: dict) -> tuple[dict, SessionSummaryForDB, dict]:
        """
        Generate summaries from the final persisted session data.
        """
        backend_data,frontend_data  = self.session_summary.generate_summary(session_data)
        return frontend_data, backend_data, active_session
        
    def stop_session(self, active_session):
        active_session["is_running"] = False
        active_session["actual_end_time"] = datetime.now()
        active_session["complete_session"] = False
        return active_session

    


    

    