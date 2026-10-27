# Unit tests

## How to run

```bash
conda env update -f environment.yml   # installs pytest (once)
pytest                                # run from the project root
```

Result right now: **32 passed, 1 xfailed** (the expected failure is a known bug, see test 8), in under a second.

## What is tested

| # | File | Part of the project | What it checks |
|---|---|---|---|
| 1 | `test_score.py` | `GenerateSummary.generate_score` | Score = productive time / session time; 0 for an empty session; always within 0–100 |
| 2 | `test_generate_summary.py` | `GenerateSummary` | Summary numbers (duration, productive time, most-used tab, most-blocked site); frontend JSON format; no crash without tabs |
| 3 | `test_session_start.py` | `SessionStart` | Minutes → seconds, end time = start + duration; can't start two sessions; new unique ID after a stop |
| 4 | `test_stop_session.py` | `StopSession` | Session marked stopped with an end time; frontend summary returned |
| 5 | `test_tab_timer.py` | `TabTimerHandler` | Switching tabs returns time spent on the previous tab; same tab twice does nothing; stop with no tab returns 0 |
| 6 | `test_tab_activity.py` | `TabActivityHandler` | Switching adds time to the old tab and marks it inactive; unknown tab rejected; closing marks the tab closed |
| 7 | `test_dirty_tabs.py` | `DirtyTabHandler` | Changed tabs returned once, then the queue is empty; only the latest version kept; tab without ID rejected |
| 8 | `test_website_blocker.py` | `WebsiteBlockerManager` | One decision per page / per recommended video; AI asked with page + topic; **xfail: unrelated pages are never blocked** |
| 9 | `test_summary_adapter.py` | `SummaryAdapter` | Valid summary converted for the database; time grouped per domain; empty topic / ID or negative duration rejected |
| 10 | `test_session_repository.py` | `SessionRepository` | Saved session reads back the same; login only with the correct token; users can't see each other's sessions |

## Best practices used (and why)

**Arrange – Act – Assert (AAA).** Every test has three parts: set up the data, call one function, check the result. It makes tests easy to read.

**One behaviour per test, with a descriptive name.** For example, `test_cannot_start_second_session_while_one_is_active`. When a test fails, the name already tells you what broke.

**FIRST principles:**
- **Fast:** the whole suite runs in ~0.2 s.
- **Independent:** each test gets fresh data from a fixture (`conftest.py`), so the order doesn't matter.
- **Repeatable:** no real clock, no network, no real database; same result every run.
- **Self-checking:** `assert` decides pass/fail; nobody reads printed output.
- **Timely:** written alongside the code, not at the end.

**Isolation with test doubles (mocks).** A unit test checks one unit only.
- `test_tab_timer.py` replaces the real clock (`monotonic`) with fake times, so we don't have to wait with `time.sleep()`.
- `test_tab_activity.py` replaces the timer with a `Mock`, so only the tab logic is tested.
- `test_website_blocker.py` replaces the AI with a `Mock` that gives a fixed answer, so the blocking logic is tested without the AI.
- `test_session_repository.py` uses `tmp_path`: a temporary, empty database per test. The real `grove.sqlite3` is never touched.

**Fixtures** (`@pytest.fixture`) hold shared test data in one place (`conftest.py`) instead of copy-pasting it.

**Parametrize** (`@pytest.mark.parametrize`) runs one test with several inputs, e.g. the different invalid summaries in test 9.

**Edge cases, not only the happy path.** Zero duration, empty tab list, missing ID, negative numbers, wrong login token, another user's data.

**Known bugs are marked, not hidden.** `@pytest.mark.xfail(strict=True)` documents a bug we know about. Once someone fixes it, the test starts passing and pytest flags it, so we remember to remove the marker.

**The tests were checked to catch bugs.** We broke the code on purpose: removing the 0–100 limit in the score made 2 tests fail, and not clearing the dirty-tab queue made 1 test fail. A test that never fails is useless.

## Bug found by the tests

`WebsiteBlockerManager.confidence_to_bool()` always returns `False`, and `block` is set to `is_related`. So no page is ever blocked, whatever the AI decides. The logic should probably be `block = not is_related`, once the AI returns real answers.
