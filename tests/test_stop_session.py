"""4. Stopping a session (StopSession)."""
from datetime import datetime

from UserSession.StopSession.StopSession import StopSession


def test_stop_session_marks_session_as_stopped_and_logs_end_time():
    active = {"is_running": True, "complete_session": False, "actual_end_time": None}

    result = StopSession().stop_session(active)

    assert result["is_running"] is False
    assert result["complete_session"] is True
    assert isinstance(result["actual_end_time"], datetime)


def test_manage_session_stop_returns_frontend_summary(session_data):
    active = {"is_running": True, "complete_session": False, "actual_end_time": None}

    frontend, backend, session_info = StopSession().manage_session_stop(session_data, active)

    assert frontend["action"] == "end_session"
    assert backend.session_topic == "Math"
    assert session_info["is_running"] is False
