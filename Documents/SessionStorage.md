# SQL session summaries: setup and recovery

The active integration follows the team's summary-only handoff. `System` calls `IDataBaseManager`; the SQL implementation stores the unchanged `SessionSummaryForDB` DTO. The session coordinator and temporary-data manager own JSON lifecycle and deletion. See the [interface contract](DatabaseInterface.md).

## Local setup

Use the repository's Python 3.12 environment (`environment.yml`) with FastAPI and Uvicorn. SQLite is built into Python; no database server or new dependency is required.

```powershell
# Once, create the intended local profile. Keep its printed key private.
python -m DataBase.manage create-user "Your name"

# Start the backend from the repository root.
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Load `Frontend/` as an unpacked browser extension and enter that profile key. Open History, then select **Past Sessions** to open its separate tab. Both views retrieve the same owner-scoped records. The extension shares its key between popup, dashboard, and background worker.

For a localhost UI preview, serve `Frontend/` on port 5173 and open `/popup.html`; actual browser tracking requires the extension. `?preview=1` explicitly uses sample data instead of SQL.

Defaults are resolved from the source location:

| Purpose | Default / override |
| --- | --- |
| Permanent SQL | `DataBase/grove.sqlite3`; override with `GROVE_SQL_PATH`. |
| Temporary team JSON | `UserSession/ActiveSessionDB/<owner-hash>/session_<id>.json`. |
| Test/custom temporary root | If `GROVE_ACTIVITY_PATH` is set, use its parent directory's `team-active/<owner-hash>/`. |

Existing configured SQLite databases and profile keys remain usable. **No SQL schema migration is required for this integration.** New summary-only sessions coexist with older detailed records. Stop the backend before copying a database backup; preserve temporary folders too. Run one backend process per temporary-data root.

## Access the database

Open the configured `.sqlite3` file with a SQLite viewer, or use the existing CLI:

```powershell
python -m DataBase.manage users
python -m DataBase.manage --help
```

The `sessions` table has normalized metadata plus JSON text columns for the complete supplied DTO and display summary. New payloads identify `detail_level: "summary"` and retain `source_summary` with all 12 original fields. `analyses` stores returned results separately; `visits`/`events` preserve older detailed archives. Application queries are scoped to `(user_id, session_id)`.

Keys are local provisioned profile credentials, not a hosted account service. Keep the backend bound to loopback. OS-level access to the SQLite file is outside the API's user isolation boundary.

## JSON preservation and migration

Existing legacy JSON and old `DataBase/active/` spools are not deleted or assigned to a user automatically. Import a source explicitly with the actual owner's ID and the backend stopped:

```powershell
python -m DataBase.manage import-legacy USER_ID "path/to/Activity.json"
python -m DataBase.manage import-legacy USER_ID "path/to/session_file.json"
```

Supported inputs include older `Activity.json` archives, individual detailed spools, prototype `Db.json`, unlinked `MetaDataDatabase.json`, and team `session_info`/`website_metadata` files. Imports preserve original files and raw source data, reserve ownership, and can resume after a partial failure. Repeating an unchanged import is a no-op. Changed sources or attempts to reassign a source to another user are rejected. Unknown measurements remain unknown; unlinked metadata is not assigned to invented sessions.

## Completion and retries

- Ending a session freezes its end time and summary in temporary JSON before SQL insertion.
- System saves the summary; only a successful save permits the session coordinator to request deletion.
- A failed save or deletion retains pending data. Checkpoints run every five seconds; requests, restart, and **Retry save** also retry it.
- Identical retries cannot duplicate a summary or overwrite returned analysis. Different content with the same ID is rejected for review.
- Restart replays a frozen DTO unchanged. Unfinished work is closed at its last saved checkpoint, excluding unknown offline time.
- Temporary writes use a sibling file, `fsync`, and replacement. A disk failure can preserve the previous durable checkpoint, not guarantee new activity was saved.

The session ID generator now uses large integers instead of the upstream 0–100 range. IDs remain exactly representable in JavaScript and retain the team's integer DTO contract.

## AI handoff and validation

The existing `/backend` actions remain `get_ai_sessions`, `get_ai_session`, and `save_session_analysis`, using a separately provisioned user-scoped AI key (`python -m DataBase.manage issue-key USER_ID --role ai`). User keys cannot perform AI actions; AI keys cannot control sessions. Returned analysis must have a nonempty `summary` and is attached to the original owner/session. For new sessions, the input contains the supplied statistics and empty detailed-activity arrays; no new model or detailed-data feed was added.

Run backend and real HTTP checks:

```powershell
python -B -m unittest discover -s tests -v
```

`tests/test_summary_integration.py` covers the actual team DTO, SQL isolation, save/cleanup failures, restart, timer completion, pause/resume, last-tab flush, ID collisions, and legacy migration. `tests/test_api.py` checks real authenticated HTTP requests and AI roles. `tests/browser_summary_dashboard.py` uses an isolated Edge extension, temporary SQL/profile data, and controlled AI results to check the popup, History, new tab, exports, search, empty/error states, and narrow layout. The browser check requires Playwright and installed Edge.
