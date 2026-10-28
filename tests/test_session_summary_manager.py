"""
12. Loading past sessions (SessionSummaryManager).

The database is replaced with a Mock, so the tests check only how past
sessions are requested and ordered, not how they are stored (see test 10).
"""
from datetime import datetime
from unittest.mock import Mock

import pytest

from System.SystemManager import SessionSummaryManager


def make_manager(history=()):
    db = Mock()
    db.get_history.return_value = list(history)
    manager = SessionSummaryManager(db)
    manager.clock = lambda: datetime(2026, 10, 28, 15, 0)   # fixed "now"
    return manager


def record(session_id, started_at):
    return {"id": session_id, "topic": "Math", "status": "ended",
            "started_at": started_at, "ended_at": started_at, "active_seconds": 600}


def test_sessions_are_listed_newest_first():
    manager = make_manager([record("old", "2026-10-20T09:00:00"),
                            record("new", "2026-10-27T09:00:00")])

    result = manager.get_past_session("get_sessions", {}, "user-1", None)

    assert [s["id"] for s in result] == ["new", "old"]


def test_only_the_users_own_history_is_requested():
    manager = make_manager()

    manager.get_past_session("get_sessions", {}, "user-1", None)

    manager.db_manager.get_history.assert_called_once_with("user-1")


def test_session_summary_includes_storage_status():
    manager = make_manager()
    manager.db_manager.get_session_details.return_value = {
        "session": {}, "summary": {"score": 75}, "storage_status": "saved"}

    result = manager.get_past_session("get_session_summary", {"session_id": "s1"}, "user-1", None)

    assert result == {"score": 75, "storage_status": "saved"}
    manager.db_manager.get_session_details.assert_called_once_with("user-1", "s1")


def test_unknown_action_raises_error():
    with pytest.raises(ValueError):
        make_manager().get_past_session("delete_everything", {}, "user-1", None)
