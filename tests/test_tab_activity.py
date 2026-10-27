"""
6. Tab switching (TabActivityHandler).

The timer is replaced with a Mock, so this test checks ONLY the
tab-switching logic, not the timer (that is tested in test_tab_timer.py).
"""
from unittest.mock import Mock

import pytest

from UserSession.MetadataProcessing.TabActivity import TabActivityHandler
from UserSession.MetadataProcessing.TabHandlers import DirtyTabHandler, InMemoryTabsStore


@pytest.fixture
def handler():
    tabs = InMemoryTabsStore()
    activity = TabActivityHandler(timer=Mock(), tabs=tabs, dirty_tabs=DirtyTabHandler())
    for tab_id in (1, 2):
        tabs.save_tab(tab_id, activity.create_metadata({"tab_id": tab_id, "url": "https://example.com"}))
    return activity


def test_activating_new_tab_adds_time_to_previous_tab(handler):
    handler.timer.is_active.return_value = False
    handler.timer.start.return_value = (1, 45.0)   # timer says: tab 1 was open for 45 s

    handler.activate_tab(2)

    assert handler.tabs.get_tab(1)["time_spent"] == 45.0
    assert handler.tabs.get_tab(1)["currently_active"] is False
    assert handler.tabs.get_tab(2)["currently_active"] is True


def test_activating_unknown_tab_returns_false(handler):
    assert handler.activate_tab(99) is False


def test_closing_tab_marks_it_closed(handler):
    handler.timer.is_active.return_value = False

    closed, tab = handler.close_tab(1)

    assert closed is True
    assert tab["currently_open"] is False
