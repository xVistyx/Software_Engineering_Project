"""7. Changed-tab queue (DirtyTabHandler)."""
import pytest

from UserSession.MetadataProcessing.TabHandlers import DirtyTabHandler


def test_dirty_tabs_are_returned_once_then_queue_is_empty():
    queue = DirtyTabHandler()
    queue.mark_dirty({"tab_id": 1, "time_spent": 10})
    queue.mark_dirty({"tab_id": 2, "time_spent": 20})

    first_read = queue.get_dirty_tabs()
    second_read = queue.get_dirty_tabs()

    assert len(first_read) == 2
    assert second_read == []


def test_same_tab_marked_twice_keeps_only_latest_version():
    queue = DirtyTabHandler()
    queue.mark_dirty({"tab_id": 1, "time_spent": 10})
    queue.mark_dirty({"tab_id": 1, "time_spent": 25})

    assert queue.get_dirty_tabs() == [{"tab_id": 1, "time_spent": 25}]


def test_tab_without_id_is_rejected():
    with pytest.raises(ValueError):
        DirtyTabHandler().mark_dirty({"title": "no id"})
