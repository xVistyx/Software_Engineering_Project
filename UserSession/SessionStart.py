from dataclasses import dataclass, asdict
from datetime import datetime
import random

@dataclass
class SessionStartInfo:
    id: int
    topic: str
    is_running: bool
    time: float
    start_time: datetime
    last_update_time: datetime



class SessionStart:
    def __init__(self):
        self.active_session = False

    def setup_session(self, content: dict):
        self.active_session = True

        session_id = self.generate_id()
        topic = content["topic"]

        # If you want to track in seconds:
        time = content["minutes"] * 60

        now = datetime.now()

        return SessionStartInfo(
            id=session_id,
            topic=topic,
            is_running=self.active_session,
            time=time,
            start_time=now,
            last_update_time=now
        )

    def generate_id(self):
        return random.randint(0, 100)

    def session_start_as_dict(self, content):
        start_session = self.setup_session(content)
        return asdict(start_session)