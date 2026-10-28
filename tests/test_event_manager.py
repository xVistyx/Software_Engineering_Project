"""
14. Browser events (EventManager).

The timer and the tab handler are Mocks: the tests only check WHEN the
active tab gets stopped, not how stopping works (that is test 6).
"""
from unittest.mock import Mock

import pytest

from UserSession.MetadataProcessing.MetaDataManager import EventManager


@pytest.fixture
def events():
    timer = Mock(active_tab_id=3)   # tab 3 is currently being timed
    tab_activity = Mock()
    tab_activity.deactivate_tab.return_value = (True, {"tab_id": 3})
    return EventManager(timer, tab_activity)


def test_leaving_the_browser_stops_the_active_tab(events):
    result = events.handle_event("window_focus_changed", "unfocused")

    assert result == (True, {"tab_id": 3})
    events.tab_activity.deactivate_tab.assert_called_once_with(3)


@pytest.mark.parametrize("state", ["idle", "locked"])
def test_idle_or_locked_computer_stops_the_active_tab(events, state):
    events.handle_event("idle_state_changed", state)

    events.tab_activity.deactivate_tab.assert_called_once_with(3)


def test_leaving_the_browser_with_no_active_tab_does_nothing(events):
    events.timer.active_tab_id = None

    assert events.handle_event("window_focus_changed", "unfocused") == (False, None)
    events.tab_activity.deactivate_tab.assert_not_called()


@pytest.mark.parametrize("reason, state", [
    ("heartbeat", None),
    ("window_focus_changed", "focused"),
    ("idle_state_changed", "active"),
])
def test_other_events_do_not_stop_the_active_tab(events, reason, state):
    assert events.handle_event(reason, state) == (False, None)
    events.tab_activity.deactivate_tab.assert_not_called()
