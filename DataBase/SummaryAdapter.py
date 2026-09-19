"""Map the team's supplied summary DTO to the existing SQL/History representation.

No session component is imported or queried here. The original field values are
retained, including naive timestamps and the team's calculated scores.
"""
from dataclasses import asdict, is_dataclass
from datetime import datetime
import math


def summary_record(user_id, data):
    raw = asdict(data) if is_dataclass(data) else dict(data)
    required = {'session_id', 'session_topic', 'session_start_time', 'session_end_time',
                'set_session_duration', 'actual_session_duration', 'productive_time', 'session_score',
                'number_of_tabs', 'time_spent_on_tabs', 'most_used_tab', 'most_often_blocked'}
    if set(raw) != required:
        raise ValueError('Expected the SessionSummaryForDB fields')
    if type(raw['session_id']) is not int or raw['session_id'] < 0:
        raise ValueError('Session ID must be a nonnegative integer')
    if not isinstance(raw['session_topic'], str) or not raw['session_topic'].strip():
        raise ValueError('Session topic is required')
    for key in ('session_start_time', 'session_end_time'):
        if isinstance(raw[key], datetime):
            raw[key] = raw[key].isoformat()
        if not isinstance(raw[key], str):
            raise ValueError('Session timestamps are required')
        datetime.fromisoformat(raw[key].replace('Z', '+00:00'))
    for key in ('set_session_duration', 'actual_session_duration', 'productive_time', 'session_score',
                'number_of_tabs', 'time_spent_on_tabs'):
        value = raw[key]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError('Summary measurements must be nonnegative finite numbers or null')
    if raw['actual_session_duration'] is None or raw['set_session_duration'] is None:
        raise ValueError('Session durations are required')
    sid = str(raw['session_id'])
    session = {'id': sid, 'user_id': user_id, 'topic': raw['session_topic'], 'status': 'ended',
               'started_at': raw['session_start_time'], 'ended_at': raw['session_end_time'],
               'planned_seconds': raw['set_session_duration'], 'active_seconds': raw['actual_session_duration'],
               'is_running': False, 'strict_mode': False, 'duration_known': True, 'detail_level': 'summary',
               'source_summary': raw, 'website_visits': [], 'events': []}
    summary = {'id': sid, 'topic': session['topic'], 'status': 'ended', 'summaryText': None,
               'startedAt': session['started_at'], 'endedAt': session['ended_at'],
               'plannedSeconds': raw['set_session_duration'], 'focusedSeconds': raw['actual_session_duration'],
               'productiveSeconds': raw['productive_time'], 'browserActiveSeconds': raw['time_spent_on_tabs'],
               'score': raw['session_score'], 'tabCount': raw['number_of_tabs'],
               'mostUsedTab': raw['most_used_tab'], 'mostOftenBlocked': raw['most_often_blocked'],
               'pausedSeconds': None, 'unattributedSeconds': None, 'visitCount': None,
               'tabsBlocked': None, 'domains': [], 'detailLevel': 'summary',
               'sessionTimeSeconds': raw['actual_session_duration'], 'productiveTimeSeconds': raw['productive_time'],
               'tabsOpened': raw['number_of_tabs'], 'distractionsBlocked': None}
    return session, summary