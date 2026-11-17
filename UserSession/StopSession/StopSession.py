from .GenerateSummary import GenerateSummary, SessionSummaryForDB
from datetime import datetime

class StopSession:
    def __init__(self):
        
        self.session_summary = GenerateSummary()

    def manage_session_stop(self, session_data: dict, active_session: dict) -> tuple[dict, SessionSummaryForDB, dict]:
        """
        set session data
        pass session data to GenerateSummary
        Stop All tracking of websites and information        
        """
        session_info = self.stop_session(active_session)
        session_data["session_info"]["actual_end_time"] = session_info["actual_end_time"]
        backend_data,frontend_data  = self.session_summary.generate_summary(session_data)
        return frontend_data, backend_data, session_info
        
    def stop_session(self, active_session):
        active_session["is_running"] = False
        active_session["complete_session"] = True
        active_session["actual_end_time"] = datetime.now()

        return active_session

    


    

    