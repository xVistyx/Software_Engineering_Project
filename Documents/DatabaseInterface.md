# Permanent-storage handoff

This integration is based directly on the colleague's `feature/StopSession` commit **bb5b28d**, including **d434500** (summary DTO) and **bb5b28d** (temporary deletion). It follows the supplied `Backend LockDown.drawio` boundary:

**System → IDataBaseManager → DataBaseManager → SQLite**

The database component receives supplied data, stores it, and returns saved records. It never calls the session manager, reads its temporary files, deletes those files, or generates a session summary.

## The supplied class

The existing [SessionSummaryForDB](../UserSession/StopSession/GenerateSummary.py) dataclass is unchanged. The storage handoff accepts precisely these 12 fields:

| Field | Storage meaning |
| --- | --- |
| `session_id` | Original integer ID; converted to a text SQL key without changing the DTO value. |
| `session_topic` | Goal/topic. |
| `session_start_time`, `session_end_time` | Datetimes serialized to ISO strings; original timezone information is preserved. |
| `set_session_duration`, `actual_session_duration` | Planned seconds and the team's actual wall-time seconds, including pauses. |
| `productive_time`, `session_score` | Values calculated by the existing session component. |
| `number_of_tabs`, `time_spent_on_tabs` | Supplied tab count and seconds spent on tabs. |
| `most_used_tab`, `most_often_blocked` | Supplied text values. |

The authenticated `user_id` is passed **separately by System**, not added to the class or accepted from the browser's request body.

```python
# System integration point:
def send_to_db_manager(self, data, user_id):
    self.db_manager.save_session(user_id, data)  # data is SessionSummaryForDB
```

[DataBaseManager](../DataBase/DataBaseManager.py) implements [IDataBaseManager](../DataBase/IDataBaseManager.py), also exported from `interfaces.py`. Its concrete methods fill the database placeholders in the teammate's UML:

| Method called by System | Result |
| --- | --- |
| `save_session(user_id, summary)` | Returns normally only after a successful SQL commit or an identical retry; raises on failure. |
| `get_history(user_id)` | Saved session records belonging to that user. |
| `get_session_details(user_id, session_id)` | Session, display summary, optional analysis, and storage status. |
| `get_preferences(...)`, `save_preferences(...)` | Existing settings/blocklist support. |
| `authenticate(token)`, `get_users()` | Existing local-profile authentication and startup recovery support. |
| `get_ai_session(...)`, `save_session_analysis(...)` | Existing owner-scoped AI input/result storage. |
| `get_legacy_sources(user_id)` | Original import data for exports. |

The SQL representation keeps all DTO fields under `session.source_summary`. A pure adapter derives the existing History response shape, so no frontend response protocol replacement is needed. A repeated owner/session ID with different summary contents raises an error rather than silently overwriting another session.

## Temporary data and cleanup

1. `UserSessionCoordinator` (in `UserSessionManager.py`) controls the active session and calls its existing timing, metadata, and stop/summary components.
2. `UserSessionDataManager` owns temporary JSON. It writes the terminal end time and frozen DTO using atomic replacement before archival.
3. System receives the DTO and calls `send_to_db_manager`.
4. After a successful commit, System calls `UserSessionCoordinator.delete_old_session(id)`.
5. The coordinator calls `UserSessionDataManager.delete_current_session_json(id)` and clears the pending record.

The colleague's original deletion call ran during `end_user_session`, before System could save anything. This integration defers that call until database success. Cleanup ownership remains with the session component. Failed saves/deletes retain the frozen summary and JSON for retry through requests, checkpoints, and restart. No new AI service is introduced.

## What can be shown

New records supply summary statistics only. History and Past Sessions display those fields and offer JSON and summary CSV exports. They do not fabricate website lists, allow/block decisions, pause durations, events, or a natural-language summary. Older SQL records and imported legacy records retain any detailed data they already contained.

The team's AI evaluator is still a stub. Stored productivity/score values are upstream calculations, not evidence of a live model. Optional later analysis attaches to the original user/session. The AI input envelope is retained; new summary-only records have no detailed `website_metadata` or events to return.

See [setup and migration](SessionStorage.md) and [updated UML](BackendUML.md).
