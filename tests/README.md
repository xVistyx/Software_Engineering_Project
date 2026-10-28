# Unit tests

## How to run

```bash
conda env update -f environment.yml   # installs pytest (once)
pytest                                # run from the project root
```

Without conda: `pip install fastapi uvicorn pydantic pytest`. If the `pytest` command is not found, use `python -m pytest` instead.

To run one file only: `python -m pytest tests/test_score.py`

Result right now: **84 passed, 2 xfailed** (the 2 expected failures are known bugs, see tests 8 and 18), in under a second.

## What is tested

Each file tests one part of the project and contains several tests. pytest counts every test function separately, and a parametrized test once per input, so the 19 files give 86 tests.

| # | File | Tests | Part of the project | What it checks |
|---|---|---|---|---|
| 1 | `test_score.py` | 4 | `GenerateSummary.generate_score` | Score = productive time / session time; 0 for an empty session; always within 0–100 |
| 2 | `test_generate_summary.py` | 3 | `GenerateSummary` | Summary numbers (duration, productive time, most-used tab, most-blocked site); frontend JSON format; no crash without tabs |
| 3 | `test_session_start.py` | 3 | `SessionStart` | Minutes → seconds, end time = start + duration; can't start two sessions; new unique ID after a stop |
| 4 | `test_stop_session.py` | 2 | `StopSession` | Session marked stopped with an end time; frontend summary returned |
| 5 | `test_tab_timer.py` | 3 | `TabTimerHandler` | Switching tabs returns time spent on the previous tab; same tab twice does nothing; stop with no tab returns 0 |
| 6 | `test_tab_activity.py` | 3 | `TabActivityHandler` | Switching adds time to the old tab and marks it inactive; unknown tab rejected; closing marks the tab closed |
| 7 | `test_dirty_tabs.py` | 3 | `DirtyTabHandler` | Changed tabs returned once, then the queue is empty; only the latest version kept; tab without ID rejected |
| 8 | `test_website_blocker.py` | 4 | `WebsiteBlockerManager` | One decision per page / per recommended video; AI asked with page + topic; **xfail: unrelated pages are never blocked** |
| 9 | `test_summary_adapter.py` | 5 | `SummaryAdapter` | Valid summary converted for the database; time grouped per domain; empty topic / ID or negative duration rejected |
| 10 | `test_session_repository.py` | 3 | `SessionRepository` | Saved session reads back the same; login only with the correct token; users can't see each other's sessions |
| 11 | `test_past_session_manager.py` | 7 | `PastSessionManager` | Seconds → minutes; "pending" vs "saved"; "this week" starts Monday 00:00; focused hours rounded to 1 decimal; zero stats for a new user; export; unknown action rejected |
| 12 | `test_session_summary_manager.py` | 4 | `SessionSummaryManager` | Past sessions listed newest first; only the user's own history is requested; summary includes storage status; unknown action rejected |
| 13 | `test_tab_manager.py` | 6 | `TabManager` | First event creates a tab, the next one updates it; event without tab ID ignored; activated tab is timed; closing marks it closed and stops its timer |
| 14 | `test_event_manager.py` | 7 | `EventManager` | Leaving the browser or an idle / locked screen stops the active tab; heartbeats and other events don't; nothing happens when no tab is active |
| 15 | `test_settings.py` | 5 | `Settings` | Defaults when nothing is saved; unknown setting ignored; settings and blocklist saved and loaded again; unknown action returns empty content |
| 16 | `test_user_session_data_manager.py` | 8 | `UserSessionDataManager` | Session file starts empty; start saved with text timestamps; tabs added (and counted) and updated; errors for a missing file; file deleted |
| 17 | `test_active_user_session.py` | 5 | `ActiveUserSessionManager` | Countdown goes down by the time passed and never below 0; new or changed tabs are saved; nothing saved when nothing changed |
| 18 | `test_user_session_coordinator.py` | 6 | `UserSessionCoordinator` | Not running before start; start, end and restart a session; unknown action returns an error; **xfail: pausing a session doesn't crash** |
| 19 | `test_authenticate_user.py` | 5 | `AuthenticateUser` | Unknown user rejected; same user always gets the same session manager, different users separate ones; registering saves the user with a unique token |

## Best practices used (and why)

**Arrange – Act – Assert (AAA).** Every test has three parts: set up the data, call one function, check the result. It makes tests easy to read.

**One behaviour per test, with a descriptive name.** For example, `test_cannot_start_second_session_while_one_is_active`. When a test fails, the name already tells you what broke.

**FIRST principles:**
- **Fast:** the whole suite runs in under a second.
- **Independent:** each test gets fresh data from a fixture (`conftest.py`), so the order doesn't matter. This was checked by running the suite in reverse order and each file on its own.
- **Repeatable:** no real clock, no network, no real database; same result every run.
- **Self-checking:** `assert` decides pass/fail; nobody reads printed output.
- **Timely:** written alongside the code, not at the end.

**Isolation with test doubles.** A unit test checks one unit only.
- **Fake clock:** `test_tab_timer.py` replaces `monotonic` and `test_active_user_session.py` replaces `datetime.now()` with fixed times, so we don't have to wait with `time.sleep()`.
- **Mocks:** `test_tab_activity.py` replaces the timer, `test_website_blocker.py` the AI, `test_session_summary_manager.py` the database and `test_event_manager.py` the timer and tab handler. A Mock gives a fixed answer and records how it was called, so a test can also check `assert_called_once_with(...)` or `assert_not_called()`.
- **Fake:** `test_authenticate_user.py` uses a tiny in-memory user database instead of a Mock. The code saves a user and immediately looks it up again, so the test double has to remember what was saved.
- **Temporary files:** `test_session_repository.py` uses `tmp_path`: a temporary, empty database per test, so the real `grove.sqlite3` is never touched. Tests 15, 16, 18 and 19 use `monkeypatch` to point file paths (or the current folder) at `tmp_path`, so the real `Settings/*.json` and `UserSession/ActiveSessionDB/` are never touched either.

**Fixtures** (`@pytest.fixture`) hold shared test data in one place (`conftest.py`, or at the top of a test file) instead of copy-pasting it.

**Parametrize** (`@pytest.mark.parametrize`) runs one test with several inputs, e.g. the different invalid summaries in test 9 or the idle / locked states in test 14.

**Edge cases, not only the happy path.** Zero duration, empty tab list, missing ID, negative numbers, wrong login token, another user's data, a user with no sessions, a countdown that would go below zero.

**Known bugs are marked, not hidden.** `@pytest.mark.xfail(strict=True)` documents a bug we know about. Once someone fixes it, the test starts passing and pytest flags it, so we remember to remove the marker.

**The tests were checked to catch bugs.** A test that never fails is useless, so we broke the code on purpose and checked that a test fails.
- Tests 1–10 were checked by hand: removing the 0–100 limit in the score made 2 tests fail, and not clearing the dirty-tab queue made 1 test fail.
- Tests 11–19 are checked by a script, `tests/mutation_check.py`. It breaks the code in 41 small ways (for example: counting time up instead of down, not loading saved settings, accepting unknown users) and runs the matching test file each time. Right now **41/41** breaks are caught. The script only changes a temporary copy of the project, never the real code. Run it with `python tests/mutation_check.py` (takes about a minute). If it prints `SKIPPED`, the code it tries to break has changed, so that line in the script needs updating.

## Bugs found by the tests

1. **No page is ever blocked (test 8).** `WebsiteBlockerManager.confidence_to_bool()` always returns `False`, and `block` is set to `is_related`. So no page is ever blocked, whatever the AI decides. The logic should probably be `block = not is_related`, once the AI returns real answers.

2. **Pausing or resuming a session crashes the backend (test 18).** The pause button sends `update_session` with `{session_id, status}`. `UserSessionCoordinator.update_user_session()` passes that message to `updated_session_state()`, which expects the active session and fails with `KeyError: 'last_update_time'`. Even past that, the function returns `frontend_message`, which is never set on this path. `main.py` only catches `ValueError`, so the frontend gets a server error. This is probably why the pause button stopped working (see `Documents/TODOS.md`).

## Not tested yet

- **The frontend** (`Frontend/`, the Chrome extension in JavaScript) has no tests yet.
- **The FastAPI endpoints** in `main.py`, i.e. the backend and frontend talking to each other over HTTP.
- **The real AI.** It is always replaced by a Mock, so the tests check the blocking logic, not whether the AI's decisions are good.
