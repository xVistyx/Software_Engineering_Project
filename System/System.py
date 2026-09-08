from System.BackendRequests import BackendRequests
from UserSession.ActivityTracker import ActivityTracker


class System:
    """Dispatch the existing frontend protocol to the persistent activity service."""

    def __init__(self, tracker=None):
        self.tracker = tracker or ActivityTracker()
        self.backend_requests = BackendRequests()

    def buildResponse(self, message):
        return {"action": message['action'],
                "content": self.tracker.handle(message['action'], message['content'])}

    def send_requests_to_frontend(self, message):
        return self.backend_requests.build_responses(message)
