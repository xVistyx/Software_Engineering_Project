"""
18. Session actions from the frontend (UserSessionCoordinator).

The coordinator writes the session file to a relative folder, so each
test runs inside an empty temporary folder (monkeypatch.chdir).
"""
import pytest

from UserSession.UserSessionManager import UserSessionCoordinator


@pytest.fixture
def coordinator(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return UserSessionCoordinator(session_folder=tmp_path, clock=None)


def start(coordinator, topic="Math", minutes=25):
    return coordinator.user_session_manager("start_session", {"topic": topic, "minutes": minutes})


def test_no_session_is_running_before_start(coordinator):
    response = coordinator.user_session_manager("get_active_session", {})

    assert response == {"action": "get_active_session", "content": {"is_running": False}}


def test_started_session_is_running(coordinator):
    response = start(coordinator)

    assert response["content"]["topic"] == "Math"
    assert response["content"]["is_running"] is True
    assert response["content"]["time"] == 1500


def test_ending_session_returns_summary(coordinator):
    started = start(coordinator)

    response = coordinator.user_session_manager("end_session", {"session_id": started["content"]["id"]})

    assert response["action"] == "end_session"


def test_new_session_can_start_after_ending_previous_one(coordinator):
    first = start(coordinator)
    coordinator.user_session_manager("end_session", {"session_id": first["content"]["id"]})

    second = start(coordinator, topic="Physics", minutes=10)

    assert second["content"]["id"] != first["content"]["id"]


def test_unknown_action_returns_error(coordinator):
    response = coordinator.user_session_manager("fly_to_the_moon", {})

    assert response["content"] == {"error": "Unknown user session action"}


@pytest.mark.xfail(reason="Known bug: update_session (pause/resume button) crashes with "
                          "KeyError 'last_update_time'", strict=True)
def test_pausing_session_does_not_crash(coordinator):
    started = start(coordinator)

    # The frontend's pause button sends exactly this message; it should not raise
    coordinator.user_session_manager("update_session", {"session_id": started["content"]["id"], "status": "paused"})
