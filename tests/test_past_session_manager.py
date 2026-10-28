"""
11. Session history (PastSessionManager).

present() receives "now" as a parameter instead of reading the real clock,
so the tests can pick a fixed date - no mocks needed.
"""
from datetime import datetime

import pytest

from PastSessions.PastSessionManager import PastSessionManager

NOW = datetime(2026, 10, 28, 15, 0)   # a Wednesday; that week started on Monday 26 Oct


def record(session_id, started_at, active_seconds, score=None):
    """A saved session, in the format the database returns it."""
    return {"id": session_id, "topic": "Math", "status": "ended",
            "started_at": started_at, "ended_at": started_at,
            "active_seconds": active_seconds, "duration_known": True,
            "source_summary": {"session_score": score}}


def test_session_list_shows_minutes_and_score():
    sessions = [record("s1", "2026-10-26T09:00:00", 1500, score=75)]

    result = PastSessionManager().present("get_sessions", sessions, set(), [], NOW)

    assert result[0]["minutes"] == 25
    assert result[0]["score"] == 75


def test_session_not_yet_saved_is_marked_pending():
    sessions = [record("s1", "2026-10-26T09:00:00", 600),
                record("s2", "2026-10-26T11:00:00", 600)]

    result = PastSessionManager().present("get_sessions", sessions, {"s1"}, [], NOW)

    assert [s["storage_status"] for s in result] == ["pending", "saved"]


def test_stats_count_only_sessions_since_monday_as_this_week():
    sessions = [record("s1", "2026-10-26T09:00:00", 600),    # Monday, this week
                record("s2", "2026-10-25T20:00:00", 600)]    # Sunday, last week

    stats = PastSessionManager().present("get_stats", sessions, set(), [], NOW)

    assert stats["total"] == 2
    assert stats["thisWeek"] == 1


def test_focused_hours_are_rounded_to_one_decimal():
    sessions = [record("s1", "2026-10-26T09:00:00", 3600),
                record("s2", "2026-10-26T11:00:00", 2400)]   # 6000 s = 1.666... h

    stats = PastSessionManager().present("get_stats", sessions, set(), [], NOW)

    assert stats["focusedHours"] == 1.7


def test_stats_for_user_without_sessions_are_zero():
    stats = PastSessionManager().present("get_stats", [], set(), [], NOW)

    assert stats["total"] == 0
    assert stats["thisWeek"] == 0
    assert stats["focusedHours"] == 0


def test_export_contains_sessions_and_export_time():
    sessions = [record("s1", "2026-10-26T09:00:00", 600)]

    export = PastSessionManager().present("export_activity", sessions, set(), [], NOW)

    assert export["sessions"] == sessions
    assert export["exported_at"] == NOW.isoformat()


def test_unknown_action_raises_error():
    with pytest.raises(ValueError):
        PastSessionManager().present("delete_everything", [], set(), [], NOW)
