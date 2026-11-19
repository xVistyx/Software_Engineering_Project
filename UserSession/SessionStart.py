from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid


@dataclass
class SessionInfo:
    id: str
    topic: str
    is_running: bool
    time: float
    start_time: datetime
    last_update_time: datetime
    predicted_end_time: datetime
    actual_end_time: datetime | None
    blocked_tabs: int
    tab_count: int
    complete_session: bool


class SessionStart:
    def __init__(self):
        self.active_session: bool = False
    


    def calculate_endtime(
        self,
        start_time: datetime,
        duration: float
    ) -> datetime:

        return start_time + timedelta(
            seconds=duration
        )


    def setup_session(
        self,
        content: dict
    ) -> SessionInfo:

        if self.active_session:
            raise RuntimeError(
                "A session is already active."
            )

        self.active_session = True

        session_id = str(uuid.uuid4())
        

        topic = content["topic"]
        time = content["minutes"] * 60

        now = datetime.now()

        return SessionInfo(
            id=session_id,
            topic=topic,
            is_running=True,
            time=time,
            start_time=now,
            last_update_time=now,
            predicted_end_time=self.calculate_endtime(
                now,
                time
            ),
            actual_end_time=None,
            blocked_tabs=0,
            tab_count=0,
            complete_session=False
        )


    def session_start_as_dict(self,content: dict) -> dict:

        start_session = self.setup_session(content)
        
        return asdict(start_session)


    def mark_session_stopped(self):
        self.active_session = False


