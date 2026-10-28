"""
16. Session file on disk (UserSessionDataManager).

The manager writes to a folder relative to the current directory, so each
test first moves into an empty temporary folder (monkeypatch.chdir).
The real UserSession/ActiveSessionDB folder is never touched.
"""
import json

import pytest

from UserSession.SessionStart import SessionStart
from UserSession.UserSessionDataManager import UserSessionDataManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return UserSessionDataManager()


@pytest.fixture
def session(manager):
    """A started session whose file has already been created."""
    session = SessionStart().session_start_as_dict({"topic": "Math", "minutes": 25})
    manager.create_session_json(session["id"])
    manager.log_session_start(session)
    return session


def test_new_session_file_is_empty(manager):
    path = manager.create_session_json("abc")

    assert json.loads(path.read_text()) == {"session_info": {}, "website_metadata": []}


def test_session_start_is_saved_with_text_timestamps(manager, session):
    saved = manager.session_end_json(session["id"])["session_info"]

    assert saved["topic"] == "Math"
    assert saved["start_time"] == session["start_time"].isoformat()


def test_writing_a_tab_adds_it_and_counts_it(manager, session):
    manager.write_metadata_to_session_json({"tab_id": 1, "time_spent": 0.0})

    saved = manager.session_end_json(session["id"])
    assert saved["website_metadata"] == [{"tab_id": 1, "time_spent": 0.0}]
    assert saved["session_info"]["tab_count"] == 1


def test_updating_a_tab_replaces_the_saved_version(manager, session):
    manager.write_metadata_to_session_json({"tab_id": 1, "time_spent": 0.0})

    updated = manager.update_metadata_in_session_json({"tab_id": 1, "time_spent": 42.0})

    assert updated is True
    assert manager.session_end_json(session["id"])["website_metadata"] == [{"tab_id": 1, "time_spent": 42.0}]


def test_updating_unknown_tab_returns_false(manager, session):
    assert manager.update_metadata_in_session_json({"tab_id": 99, "time_spent": 0.0}) is False


def test_writing_before_session_file_exists_raises_error(manager):
    with pytest.raises(RuntimeError):
        manager.write_metadata_to_session_json({"tab_id": 1, "time_spent": 0.0})


def test_reading_missing_session_raises_error(manager):
    with pytest.raises(FileNotFoundError):
        manager.session_end_json("does-not-exist")


def test_deleting_session_removes_its_file(manager, session):
    path = manager.session_path

    manager.delete_current_session_json()

    assert not path.exists()
