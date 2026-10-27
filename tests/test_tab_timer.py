"""
5. Tab timer (TabTimerHandler).

The real clock is replaced with a fake one (unittest.mock.patch), so the
tests are fast and give the same result every run - no time.sleep().
"""
from unittest.mock import patch

from UserSession.MetadataProcessing.TabHandlers import InMemoryTabsStore
from UserSession.MetadataProcessing.TabTimer import TabTimerHandler

CLOCK = "UserSession.MetadataProcessing.TabTimer.monotonic"


def test_switching_tabs_returns_time_spent_on_previous_tab():
    timer = TabTimerHandler(InMemoryTabsStore())

    with patch(CLOCK, side_effect=[100.0, 130.0, 130.0]):
        timer.start(1)                       # tab 1 starts at t=100
        previous, elapsed = timer.start(2)   # switch to tab 2 at t=130

    assert previous == 1
    assert elapsed == 30.0
    assert timer.is_active(2)


def test_starting_same_tab_twice_does_nothing():
    timer = TabTimerHandler(InMemoryTabsStore())
    timer.start(1)

    assert timer.start(1) == (None, 0.0)


def test_stop_without_active_tab_returns_zero():
    timer = TabTimerHandler(InMemoryTabsStore())

    assert timer.stop(None) == (None, 0.0)
