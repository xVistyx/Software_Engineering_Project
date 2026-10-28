"""
Checks that the tests catch bugs: breaks the code on purpose and expects a test to fail.

Run from the project root:  python tests/mutation_check.py

Every break is made in a temporary COPY of the project, which is deleted at
the end, so the real code is never changed. Takes about a minute.
Not a test itself (pytest only collects test_*.py files).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

# (test file, source file, description, old text, new text)
MUTATIONS = [
    # 11 PastSessionManager
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "minutes not converted from seconds",
     "'minutes': s['active_seconds'] / 60", "'minutes': s['active_seconds']"),
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "pending/saved swapped",
     "'pending' if s['id'] in pending_ids else 'saved'", "'saved' if s['id'] in pending_ids else 'pending'"),
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "this-week comparison reversed",
     "s['started_at'] >= monday", "s['started_at'] <= monday"),
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "focused hours not rounded to 1 decimal",
     "/ 3600, 1)", "/ 3600)"),
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "export time missing",
     "'exported_at': now.isoformat()", "'exported_at': None"),
    ("test_past_session_manager.py", "PastSessions/PastSessionManager.py", "unknown action silently accepted",
     "raise ValueError('Unknown history action')", "return None"),
    # 12 SessionSummaryManager
    ("test_session_summary_manager.py", "System/SystemManager.py", "sessions sorted oldest first",
     "reverse=True", "reverse=False"),
    ("test_session_summary_manager.py", "System/SystemManager.py", "history requested for wrong user",
     "self.db_manager.get_history(user_id)}", "self.db_manager.get_history('someone-else')}"),
    ("test_session_summary_manager.py", "System/SystemManager.py", "storage_status dropped from summary",
     "return {**details['summary'],'storage_status': details['storage_status']}", "return details['summary']"),
    ("test_session_summary_manager.py", "System/SystemManager.py", "unknown action silently accepted",
     "raise ValueError('Unknown action')", "return []"),
    # 13 TabManager
    ("test_tab_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "new tab reported as not new",
     "new_tab = True", "new_tab = False"),
    ("test_tab_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "tab update ignored",
     "self.tab_activity.update_metadata(metadata,content)", "pass"),
    ("test_tab_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "missing tab_id not checked",
     'content.get("tab_id")\n        if tab_id is None:', 'content.get("tab_id")\n        if False:'),
    ("test_tab_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "activated tab not timed",
     'reason == "tab_activated"', 'reason == "tab_activated_typo"'),
    ("test_tab_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "closed tab not returned",
     "return False, metadata if closed else None", "return False, None"),
    # 14 EventManager
    ("test_event_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "locked screen ignored",
     'state in {"idle", "locked"}', 'state in {"idle"}'),
    ("test_event_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "focus check ignores state",
     'reason == "window_focus_changed" and state == "unfocused"', 'reason == "window_focus_changed"'),
    ("test_event_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "heartbeat stops the tab",
     'if reason == "heartbeat":', 'if reason == "heartbeat":\n            return self.browser_unfocused()\n        if False:'),
    ("test_event_manager.py", "UserSession/MetadataProcessing/MetaDataManager.py", "stops a tab when none is active",
     "tab_id = self.timer.active_tab_id", "tab_id = self.timer.active_tab_id or 0"),
    # 15 Settings
    ("test_settings.py", "Settings/Settings.py", "wrong default minutes",
     '"defaultMinutes" : 45', '"defaultMinutes" : 40'),
    ("test_settings.py", "Settings/Settings.py", "unknown settings accepted",
     "if ele in self.settings:", "if True:"),
    ("test_settings.py", "Settings/Settings.py", "saved settings not loaded",
     "self.settings = json.load(fp)", "json.load(fp)"),
    ("test_settings.py", "Settings/Settings.py", "blocklist update ignored",
     'self.blocklist["sites"] = content["sites"]', "pass"),
    ("test_settings.py", "Settings/Settings.py", "unknown action returns content",
     'return {"action":action, "content": {}}', 'return {"action":action, "content": self.settings}'),
    # 16 UserSessionDataManager
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "new file not empty",
     '"session_info": {},', '"session_info": {"x": 1},'),
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "start time saved in wrong format",
     '"start_time": content["start_time"].isoformat(),', '"start_time": str(content["start_time"]),'),
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "tab count not increased",
     'database["session_info"]["tab_count"] += 1', 'database["session_info"]["tab_count"] += 0'),
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "tab update not saved",
     'database["website_metadata"][index] = metadata', "pass"),
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "unknown tab reported as updated",
     "return False", "return True"),
    ("test_user_session_data_manager.py", "UserSession/UserSessionDataManager.py", "file not deleted",
     "self.session_path.unlink()", "pass"),
    # 17 ActiveUserSessionManager
    ("test_active_user_session.py", "UserSession/ActiveUserSession.py", "time counts up instead of down",
     'active_session["time"] -= seconds_spent', 'active_session["time"] += seconds_spent'),
    ("test_active_user_session.py", "UserSession/ActiveUserSession.py", "time can go negative",
     'active_session["time"] = max(0,active_session["time"])', "pass"),
    ("test_active_user_session.py", "UserSession/ActiveUserSession.py", "last update time not saved",
     'active_session["last_update_time"] = current_time', "pass"),
    ("test_active_user_session.py", "UserSession/ActiveUserSession.py", "always saves, even with no changes",
     "stored = len(dirty_tabs) > 0", "stored = True"),
    # 18 UserSessionCoordinator
    ("test_user_session_coordinator.py", "UserSession/UserSessionManager.py", "session reported running before start",
     '"is_running": False', '"is_running": True'),
    ("test_user_session_coordinator.py", "UserSession/UserSessionManager.py", "session never marked stopped",
     "self.session_start.mark_session_stopped()", "pass"),
    ("test_user_session_coordinator.py", "UserSession/UserSessionManager.py", "end returns wrong summary",
     "        return frontend_info", "        return backend_info"),
    ("test_user_session_coordinator.py", "UserSession/UserSessionManager.py", "unknown action gives no error",
     '{"error": "Unknown user session action"}', "{}"),
    # 19 AuthenticateUser
    ("test_authenticate_user.py", "System/SystemManager.py", "unknown users accepted",
     'raise ValueError("Unknown user")', "pass"),
    ("test_authenticate_user.py", "System/SystemManager.py", "session manager not reused",
     "self.session_managers[user_id] = manager", "return manager"),
    ("test_authenticate_user.py", "System/SystemManager.py", "every user gets the same token",
     "token = secrets.token_urlsafe(32)", 'token = "same-token"'),
]


def run_tests(work, test_file=None):
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"]
    if test_file:
        cmd.append(f"tests/{test_file}")
    return subprocess.run(cmd, cwd=work, capture_output=True, text=True).returncode


def main():
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp) / "project_copy"
        shutil.copytree(PROJECT, work, ignore=shutil.ignore_patterns(
            ".git", "Frontend", "Documents", "node_modules", "__pycache__", ".pytest_cache",
            "*.sqlite3", "ActiveSessionDB", ".venv", "venv"))

        if run_tests(work) != 0:
            sys.exit("The tests already fail before breaking anything - fix those first.")
        print("Baseline: all tests pass in the copy\n")

        caught = 0
        for test_file, source, description, old, new in MUTATIONS:
            path = work / source
            original = path.read_text(encoding="utf-8")
            count = original.count(old)
            if count != 1:
                print(f"SKIPPED  {description}: text found {count} times in {source} (code changed?)")
                continue
            path.write_text(original.replace(old, new), encoding="utf-8")
            code = run_tests(work, test_file)
            path.write_text(original, encoding="utf-8")   # undo the break

            if code == 1:
                caught += 1
                result = "CAUGHT "
            elif code == 0:
                result = "MISSED "
            else:
                result = f"ERROR{code}"
            print(f"{result}  {test_file:36} {description}")

        print(f"\n{caught}/{len(MUTATIONS)} deliberate bugs caught by the tests")


if __name__ == "__main__":
    main()
