"""Four tests for the parts of the session pipeline implemented today.

NOTE: Stop-session and summary generation are placeholders in this source snapshot.
These tests do NOT claim to verify those unfinished operations or SQL persistence.
"""
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

from UserSession.UserSessionManager import UserSessionCoordinator
from UserSession.UserSessionDataManager import UserSessionDataManager
from DataBase.DataBaseManager import DataManager


@contextmanager
def temporary_project_storage():
    """Isolate file-based managers from real project data."""
    original = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        try:
            os.chdir(directory)
            yield Path(directory)
        finally:
            os.chdir(original)


class TestSessionPipelineUnit(unittest.TestCase):
    def test_new_session_is_initialized_correctly(self):
        """
        UNIT TEST: Verify that a new session starts with
        the correct initial information.

        A new session should have no tracked websites
        and should be ready to record activity.
        """

        with temporary_project_storage():

            # ARRANGE: Create a new session
            manager = UserSessionDataManager()

            # ACT: Initialize session 42
            manager.create_session_json(42)

            # ASSERT: Check the session's initial state
            saved_session = json.loads(manager.session_path.read_text())

            self.assertEqual(
                saved_session["website_metadata"], []
            )

    def test_get_active_session_returns_latest_running_session(self):
        """UNIT: active-session lookup uses the injected DB dependency."""
        manager = UserSessionDataManager()
        fake_db = Mock()
        fake_db.read_from_db.return_value = [
            {"id": 1, "is_running": False},
            {"id": 2, "is_running": True},
            {"id": 3, "is_running": True},
        ]
        manager.set_global_data_manager(fake_db)
        self.assertEqual(manager.get_active_session()["id"], 3)
        fake_db.read_from_db.assert_called_once_with("sessions")


class TestSessionPipelineIntegration(unittest.TestCase):
    def test_start_session_persists_session_information(self):
        """INTEGRATION: coordinator -> SessionStart -> file-backed session manager."""
        with temporary_project_storage():
            coordinator = UserSessionCoordinator()
            response = coordinator.user_session_manager(
                "start_session", {"topic": "Math", "minutes": 30}, DataManager()
            )
            self.assertEqual(response["action"], "start_session")
            self.assertTrue(response["content"]["is_running"])
            saved = json.loads(coordinator.user_session_data_manager.session_path.read_text())
            self.assertEqual(saved["session_info"]["id"], response["content"]["id"])
            self.assertEqual(saved["session_info"]["topic"], "Math")
            self.assertEqual(saved["session_info"]["time"], 1800)
            self.assertTrue(saved["session_info"]["is_running"])

    def test_metadata_persists_through_manager_to_fresh_database_instance(self):
        """INTEGRATION: session metadata -> file store -> JSON database -> reload."""
        with temporary_project_storage():
            session = UserSessionDataManager()
            session.create_session_json(42)
            session.session_path.write_text(json.dumps({
                "session_info": {"id": 42, "tab_count": 0}, "website_metadata": []
            }))
            session.write_metadata_to_session_json({
                "tab_id": 7, "url": "https://example.com", "time_spent": 65.0
            })
            session_data = json.loads(session.session_path.read_text())
            adapter = DataManager()
            for tab in session_data["website_metadata"]:
                adapter.write_to_db("website_metadata", {"session_id": 42, **tab})
            loaded = DataManager().read_from_db("website_metadata")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["session_id"], 42)
            self.assertEqual(loaded[0]["tab_id"], 7)
            self.assertEqual(loaded[0]["time_spent"], 65.0)


if __name__ == "__main__":
    unittest.main()
