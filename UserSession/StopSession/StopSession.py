from .GenerateSummary import GenerateSummary
class StopSession:
    def __init__(self):
        self.session_data:dict = {}

    def manage_session_stop(self, session_data: dict, frontend_content: dict):
        """
        set session data
        pass session data to GenerateSummary
        Stop All tracking of websites and information

        What frontend expects to return
        focusedSeconds
        visitCount
        pauseCount
        browserActiveSeconds
        pausedSeconds
        
        """
        self.session_data = session_data
        
        


    def generate_summary(self):
        ...

    def stop_tracking(self):
        ...
    

    