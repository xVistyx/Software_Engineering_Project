from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from collections import Counter



@dataclass
class SessionSummaryForDB:
    session_id: int
    session_topic: str
    session_start_time: datetime
    session_end_time: datetime
    set_session_duration: float
    actual_session_duration: float
    productive_time: float
    session_score: int
    number_of_tabs: int
    time_spent_on_tabs: int
    most_used_tab: str
    most_often_blocked: str


class GenerateSummary:

    def __init__(self):
        pass

    def generate_summary(self,session_data: dict) -> tuple[SessionSummaryForDB, dict]:

        session = self.session_summary_backend(session_data)
        frontend_data = self.session_summary_frontend(session,session_data)

        return session, frontend_data

  

    def session_summary_backend(self,session_data: dict) -> SessionSummaryForDB:
        """
        Creates the detailed summary that can later be stored
        in the database.
        """
        metadata: list[dict] = session_data.get("website_metadata", [])
        session_info = session_data.get("session_info", {})
        session_id = session_info.get("id")
        session_topic = session_info.get("topic")
        

        session_start_time = self._parse_datetime(session_info.get("start_time"))

        session_end_time = self._parse_datetime(session_info.get("actual_end_time"))

        # Safety fallback if generate_summary gets called before
        # actual_end_time has been written.
        if session_end_time is None:
            session_end_time = datetime.now()

        session_set_duration = self.calculate_set_duration(session_info)
        actual_session_duration = self.calculate_session_duration(session_start_time,session_end_time)
        number_of_tabs = session_info.get("tab_count",len(session_data.get("website_metadata", [])))
        time_spent_on_tabs = int(round(sum(self.calculate_time_spent_per_tab(metadata).values())))
        most_used_tab = self.calculate_most_used_tabs(metadata)
        most_often_blocked = self.calculate_most_blocked(metadata)
        productive_time = sum(float(tab.get("time_spent", 0) or 0) for tab in metadata if tab.get("is_related") is True)
        session_score = self.generate_score(productive_time, actual_session_duration)

       

        return SessionSummaryForDB(
            session_id= session_id,
            session_topic= session_topic,
            session_start_time=session_start_time,
            session_end_time=session_end_time,
            set_session_duration=session_set_duration,
            actual_session_duration=actual_session_duration,
            session_score=session_score,
            productive_time = productive_time,
            number_of_tabs=number_of_tabs,
            time_spent_on_tabs=time_spent_on_tabs,
            most_used_tab=most_used_tab,
            most_often_blocked=most_often_blocked
        )

    # ---------------------------------------------------------
    # FRONTEND SUMMARY
    # ---------------------------------------------------------

    def session_summary_frontend(self,session: SessionSummaryForDB,session_data: dict) -> dict:
        """
        Returns only the information required by the frontend.

        Expected format:

        {
            "score": ...,
            "sessionTimeSeconds": ...,
            "productiveTimeSeconds": ...,
            "distractionsBlocked": ...,
            "tabsOpened": ...
        }
        """

        metadata = session_data.get("website_metadata", [])
        session_info = session_data.get("session_info", {})

        distractions_blocked = session_info.get("blocked_tabs",sum(1 for tab in metadata if tab.get("block") is True))

        return {
            "action": "end_session",
            "content": {
                "score": session.session_score,
                "sessionTimeSeconds": int(round(session.actual_session_duration)),
                "productiveTimeSeconds": int(round(session.productive_time)),
                "distractionsBlocked": distractions_blocked,
                "tabsOpened": session.number_of_tabs
            }
        }

    def generate_score(self, productive_time: float, total_time: float) -> int:
        """
        Score = productive time / actual session duration.

        Example:
            productive time = 450 seconds
            session duration = 600 seconds

            score = 75
        """
        if total_time <= 0:
            return 0

        score = (productive_time / total_time) * 100
        score = max(0, min(100, score))

        return int(round(score))

 

    def calculate_most_used_tabs(self, metadata: list[dict]) -> str:

        if not metadata:
            return "None"

        most_used = max(metadata,key=lambda tab: float(tab.get("time_spent", 0) or 0) )

        return most_used.get("title",most_used.get("url", "Unknown"))



    def calculate_session_duration(self,start_time: datetime, end_time: datetime) -> float:

        if start_time is None or end_time is None:
            return 0.0

        duration = (end_time - start_time).total_seconds()

        return max(0.0, duration)

 

    def calculate_set_duration(self,session_info: dict) -> float:
        """
        Calculates how long the user originally intended
        the session to run.

        predicted_end_time - start_time is used instead of
        relying only on `time`, because `time` may later
        represent remaining session time.
        """

        start_time = self._parse_datetime(session_info.get("start_time"))

        predicted_end_time = self._parse_datetime(session_info.get("predicted_end_time"))

        if start_time and predicted_end_time:

            duration = (predicted_end_time - start_time).total_seconds()

            return max(0.0, duration)

        # Fallback
        return float(
            session_info.get("time", 0) or 0
        )

    def calculate_time_spent_per_tab(self, metadata: list[dict]) -> dict:
        tab_times = {}

        for tab in metadata:
            tab_id = tab.get("tab_id")

            if tab_id is None:
                continue

            tab_times[tab_id] = self._get_tab_time_spent(tab)

        return tab_times

    # ---------------------------------------------------------
    # MOST BLOCKED WEBSITE
    # ---------------------------------------------------------

    def calculate_most_blocked(self,metadata: list[dict]) -> str:

    
        blocked_sites = []

        for tab in metadata:

            if tab.get("block") is not True:
                continue

            url = tab.get("url", "")

            domain = self._get_domain(url)

            if domain:
                blocked_sites.append(domain)

        if not blocked_sites:
            return "None"

        counts = Counter(blocked_sites)

        most_blocked, _ = counts.most_common(1)[0]

        return most_blocked

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _parse_datetime(self,value) -> datetime | None:

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):

            try:
                # Also supports timestamps ending in Z.
                return datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )

            except ValueError:
                return None

        return None

    def _get_domain(self,url: str) -> str:

        if not url:
            return ""

        try:
            domain = urlparse(url).netloc

            if domain.startswith("www."):
                domain = domain[4:]

            return domain

        except ValueError:
            return ""

    def _get_tab_time_spent(self, tab: dict) -> float:
        time_spent = float(tab.get("time_spent", 0) or 0)

        # Use the recorded value if the timer has already tracked time.
        if time_spent != 0.0:
            return time_spent

        start_time = self._parse_datetime(tab.get("timestamp"))

        if start_time is None:
            return 0.0

        # Avoid mixing timezone-aware and timezone-naive datetimes.
        if start_time.tzinfo is not None:
            current_time = datetime.now(start_time.tzinfo)
        else:
            current_time = datetime.now()

        elapsed = (current_time - start_time).total_seconds()

        return max(0.0, elapsed)