"""3. Starting a session (SessionStart)."""
from datetime import timedelta

import pytest

from UserSession.SessionStart import SessionStart


def test_new_session_converts_minutes_to_seconds_and_sets_end_time():
    starter = SessionStart()

    session = starter.setup_session({"topic": "Math", "minutes": 25})

    assert session.topic == "Math"
    assert session.time == 1500
    assert session.is_running is True
    assert session.actual_end_time is None
    assert session.predicted_end_time - session.start_time == timedelta(minutes=25)


def test_cannot_start_second_session_while_one_is_active():
    starter = SessionStart()
    starter.setup_session({"topic": "Math", "minutes": 25})

    with pytest.raises(RuntimeError):
        starter.setup_session({"topic": "Physics", "minutes": 10})


def test_new_session_can_start_after_previous_was_stopped():
    starter = SessionStart()
    first = starter.setup_session({"topic": "Math", "minutes": 25})
    starter.mark_session_stopped()

    second = starter.setup_session({"topic": "Physics", "minutes": 10})

    assert second.id != first.id   # every session gets its own unique ID
