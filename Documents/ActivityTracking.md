# Session and website activity

New sessions are saved in `DataBase/Activity.json`. This is a local, versioned JSON document with persistent settings, a blocklist, and sessions. The file is excluded from Git because it contains browsing activity. The older `Db.json` and `MetaDataDatabase.json` files are preserved; their prototype records cannot reliably be linked to sessions or reconstructed into accurate durations. They are not included in the new History view or exports.

## View and export

Open **History** in the extension, select a session, and review its totals, website breakdown, and timeline. **Export JSON** includes the complete session, events, visits, and summary. **Visits CSV** exports one row per observed visit. **Export all sessions (JSON)** exports all records from the new tracker, including active and interrupted sessions. Exports of active sessions are snapshots; download them again for updated totals.

## What is recorded

- Session UUID, topic, planned duration, UTC start/end times, status, end reason, and strict-mode setting at start.
- Start, pause, resume, end, automatic completion, interruption, browser-state changes, website entry, title changes, and tracking-gap events.
- Each visit's session UUID, tab/window IDs, URL, domain, title, favicon URL, initial audible/pinned flags, start/end times, observed duration, observation count, and entry/exit reasons.
- Running time, paused time, longest uninterrupted running interval, pause count, visit count, unique domains, and per-domain totals.

URLs retain paths and query strings. Credentials and fragments are omitted. Page contents, keystrokes, form contents, and private-window activity are not collected. Collection requires a matching running session on both the extension and backend. Paused or ended sessions reject website observations, including delayed messages carrying an old session ID.

## Meaning and limits of the times

All durable timestamps use UTC; the History screen displays local time. Durations are seconds. `active_seconds` counts time the session timer runs, including work outside the browser. The compatibility summary field `focusedSeconds` refers to this running time; it does not measure attention. No focus score or distraction count is invented.

Website durations count the foreground HTTP(S) tab while the browser is focused and the machine reports active. Switching tabs, navigation, closing tabs, losing browser focus, entering idle/locked state, pausing, and ending sessions close the previous interval. Repeated observations of the same tab and URL extend the existing visit rather than creating duplicate visits.

The extension sends a heartbeat roughly every 30 seconds while running. Website attribution expires 45 seconds after the last observation, so a browser crash, stopped worker, delayed alarm, or disconnected backend cannot keep crediting a site indefinitely. Small undetected gaps may still be attributed until that timeout; late heartbeats create a new interval. Idle detection uses a 60-second input-inactivity threshold, so passive reading can be classified as idle. These are observations and estimates, not proof of attention or an exact time-on-page measurement.

`unattributedSeconds` is running time without an observed foreground website. It may represent another application, an internal browser page, idle time, or missing observations. It is not automatically distraction time. Client timestamps are retained for audit; server receipt times drive accounting, avoiding double counting caused by client clock differences or delayed messages.

## Persistence and recovery

The backend checkpoints every five seconds and on API changes, using a lock and atomic file replacement. Timers complete even when the popup is closed. Run one backend process/worker against a given activity file.

After a backend restart, any unfinished new-format session is marked `interrupted` at its last saved checkpoint; the offline gap is not counted. Start a new session to continue. A crash may lose activity since the last checkpoint. Browser inactivity alone does not pause the session timer, but it stops website attribution once detected or timed out.

## API

Send `POST /backend` with `{ "action": "...", "content": {} }`. Responses retain the action and contain an object or list. Invalid requests return HTTP 400/422 instead of a fabricated success.

| Action | Content |
| --- | --- |
| `start_session` | `topic`, integer `minutes` (1–480) |
| `get_active_session` | Empty object |
| `update_session` | `session_id`, `status`: `paused` or `running` |
| `end_session` | `session_id` |
| `log_meta_data` | `session_id`, unique `event_id`, state, reason, optional website fields |
| `get_sessions`, `get_stats` | Empty object |
| `get_session_summary`, `get_session_details` | `session_id` |
| `export_activity` | Empty object |
| `get_settings`, `update_settings` | Empty object or changed preferences |
| `get_blocklist`, `update_blocklist` | Empty object or `sites` array |

Settings and blocklist values are persistent. Strict mode is enforced by the backend for a session that started with it enabled. Site blocking, sounds, and break notifications are not implemented by this change; saving those preferences does not enable their effects.

## Development

Run the backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Reload the unpacked `Frontend` extension after code changes. The `idle` permission is required for the new inactivity detection. A standalone frontend at `http://127.0.0.1:5173/popup.html` can manage sessions and history, but website observations come from the installed extension.

Tests use temporary databases:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

`GROVE_ACTIVITY_PATH` can select a separate database for integration tests. The default resolves from the source location, independently of the working directory. Existing prototype classes remain in the repository for reference; `System` now dispatches to `UserSession/ActivityTracker.py`.

Browser API references: [idle detection](https://developer.chrome.com/docs/extensions/reference/api/idle) and [alarm scheduling and sleep behavior](https://developer.chrome.com/docs/extensions/reference/api/alarms).
