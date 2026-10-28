"""
15. User settings (Settings).

Settings are saved in JSON files. Before every test, monkeypatch points
those file paths to a temporary folder (tmp_path), so the real
Settings/settings.json and Settings/blocklist.json are never touched.
"""
import pytest

import Settings.Settings as settings_module
from Settings.Settings import Settings


@pytest.fixture(autouse=True)
def temp_settings_files(tmp_path, monkeypatch):
    # autouse: runs for every test in this file, so no test can forget it
    monkeypatch.setattr(settings_module, "settingfile", str(tmp_path / "settings.json"))
    monkeypatch.setattr(settings_module, "blocklistfile", str(tmp_path / "blocklist.json"))


def test_defaults_are_used_when_nothing_is_saved():
    settings = Settings()

    assert settings.get_settings()["content"]["defaultMinutes"] == 45
    assert settings.get_blocklist()["content"] == {"sites": []}


def test_unknown_setting_is_ignored():
    response = Settings().update_settings({"defaultMinutes": 30, "unknownSetting": True})

    assert response["content"]["defaultMinutes"] == 30
    assert "unknownSetting" not in response["content"]


def test_saved_settings_are_loaded_next_time():
    Settings().update_settings({"sounds": False})

    assert Settings().get_settings()["content"]["sounds"] is False


def test_saved_blocklist_is_loaded_next_time():
    Settings().update_blocklist({"sites": ["youtube.com"]})

    assert Settings().get_blocklist()["content"]["sites"] == ["youtube.com"]


def test_unknown_action_returns_empty_content():
    response = Settings().settings_manager("reset_everything", {})

    assert response == {"action": "reset_everything", "content": {}}
