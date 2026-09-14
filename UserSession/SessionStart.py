from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import random

@dataclass
class SessionInfo:
    id: int
    topic: str
    is_running: bool
    time: float
    start_time: datetime
    last_update_time: datetime
    predicted_end_time: datetime
    actual_end_time: datetime
    blocked_tabs: int
    tab_count: int
    complete_session: bool



class SessionStart:
    def __init__(self):
        self.active_session:bool = False

    def calculate_endtime(self, start_time: datetime, duration: float) -> datetime:
        return start_time + timedelta(seconds=duration)

    def setup_session(self, content: dict) -> SessionInfo:
        self.active_session = True

        session_id = self.generate_id()
        topic = content["topic"]

        # If you want to track in seconds:
        time = content["minutes"] * 60

        now = datetime.now()

        return SessionInfo(
            id=session_id,
            topic=topic,
            is_running=self.active_session,
            time=time,
            start_time=now,
            last_update_time=now,
            predicted_end_time= self.calculate_endtime(now, time),
            actual_end_time= None,
            blocked_tabs= 0,
            tab_count= 0,
            complete_session= False # this is for the eval and display it is used for checking if the user actually completed the session or quit early

        )

    def generate_id(self) -> int:
        return random.randint(0, 100)



    def session_start_as_dict(self, content) -> dict:
        start_session = self.setup_session(content)
        return asdict(start_session)
