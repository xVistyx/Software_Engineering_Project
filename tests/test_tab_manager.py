"""
13. Opening, updating and closing tabs (TabManager).

Uses the real tab store, timer and tab handler. The tests only check which
tabs exist and what is stored about them, never how much time was measured,
so the real clock doesn't affect the result.
"""
import pytest

from UserSession.MetadataProcessing.MetaDataManager import TabManager
from UserSession.MetadataProcessing.TabActivity import TabActivityHandler
from UserSession.MetadataProcessing.TabHandlers import DirtyTabHandler, InMemoryTabsStore
from UserSession.MetadataProcessing.TabTimer import TabTimerHandler

KHAN = {"tab_id": 1, "title": "Khan Academy", "url": "https://www.khanacademy.org"}


@pytest.fixture
def manager():
    tabs = InMemoryTabsStore()
    timer = TabTimerHandler(tabs)
    activity = TabActivityHandler(timer, tabs, DirtyTabHandler())
    return TabManager(timer=timer, tab_activity=activity, tabs=tabs)


def test_first_event_for_a_tab_creates_it(manager):
    is_new, tab = manager.handle_tab_state("page_updated", "active", KHAN, "Math")

    assert is_new is True
    assert manager.tabs.contains(1)
    assert tab["title"] == "Khan Academy"


def test_second_event_for_same_tab_updates_it(manager):
    manager.handle_tab_state("page_updated", "active", KHAN, "Math")

    is_new, tab = manager.handle_tab_state("page_updated", "active", {**KHAN, "title": "Algebra"}, "Math")

    assert is_new is False
    assert tab["title"] == "Algebra"


def test_event_without_tab_id_is_ignored(manager):
    assert manager.handle_tab_state("page_updated", "active", {"title": "?"}, "Math") == (False, None)


def test_activated_tab_starts_being_timed(manager):
    manager.handle_tab_state("tab_activated", "active", KHAN, "Math")

    assert manager.timer.is_active(1)


def test_closing_tab_marks_it_closed_and_stops_its_timer(manager):
    manager.handle_tab_state("tab_activated", "active", KHAN, "Math")

    is_new, tab = manager.handle_tab_state("tab_closed", None, {"tab_id": 1}, "Math")

    assert is_new is False
    assert tab["currently_open"] is False
    assert not manager.timer.is_active(1)


def test_closing_unknown_tab_returns_nothing(manager):
    assert manager.handle_tab_state("tab_closed", None, {"tab_id": 99}, "Math") == (False, None)
