"""
17. Active session (ActiveUserSessionManager).

The countdown reads datetime.now(), so the clock is replaced with a fixed
time (unittest.mock.patch). The metadata evaluator is a Mock, so only the
"should this be saved?" decision is tested, not the tab logic (tests 13-14).
"""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from UserSession.ActiveUserSession import ActiveUserSessionManager

CLOCK = "UserSession.ActiveUserSession.datetime"
START = datetime(2026, 10, 27, 10, 0, 0)


@pytest.fixture
def active():
    return ActiveUserSessionManager(website_meta_data=Mock(), ai_eval=Mock(), website_blocking_manager=Mock())


def test_remaining_time_goes_down_by_elapsed_seconds(active):
    session = {"time": 1500, "last_update_time": START}

    with patch(CLOCK) as clock:
        clock.now.return_value = START + timedelta(seconds=30)
        response = active.updated_session_state(session)

    assert response["content"]["time"] == 1470
    assert response["content"]["last_update_time"] == START + timedelta(seconds=30)


def test_remaining_time_never_goes_below_zero(active):
    session = {"time": 60, "last_update_time": START}

    with patch(CLOCK) as clock:
        clock.now.return_value = START + timedelta(minutes=10)
        response = active.updated_session_state(session)

    assert response["content"]["time"] == 0


def test_new_tab_is_returned_to_be_saved(active):
    evaluator = active.website_meta_data_evaluator
    evaluator.handle_event.return_value = True   # evaluator says: this is a new tab
    evaluator.get_website_meta_data.return_value = {"tab_id": 1}

    data, stored = active.webiste_data({"tab_id": 1}, "Math")

    assert data == {"tab_id": 1}
    assert stored is True


def test_changed_tabs_are_returned_to_be_saved(active):
    evaluator = active.website_meta_data_evaluator
    evaluator.handle_event.return_value = False
    evaluator.get_dirty_tabs.return_value = [{"tab_id": 1}, {"tab_id": 2}]

    data, stored = active.webiste_data({"tab_id": 2}, "Math")

    assert data == [{"tab_id": 1}, {"tab_id": 2}]
    assert stored is True


def test_nothing_is_saved_when_no_tab_changed(active):
    evaluator = active.website_meta_data_evaluator
    evaluator.handle_event.return_value = False
    evaluator.get_dirty_tabs.return_value = []

    _, stored = active.webiste_data({"tab_id": 1}, "Math")

    assert stored is False
