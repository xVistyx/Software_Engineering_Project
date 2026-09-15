"""Offline support for previously recorded detailed sessions; no runtime tracking."""
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4


def close_interrupted(record):
    at = record['checkpoint']
    for visit in record['website_visits']:
        if visit.get('ended_at') is None:
            end = min(at, visit.get('last_seen_epoch', at) + 45)
            visit['duration_seconds'] += max(0, end - visit.get('accounted_at', end))
            visit['ended_at'] = datetime.fromtimestamp(end, timezone.utc).isoformat()
            visit['end_reason'] = 'legacy_import'
    ended = datetime.fromtimestamp(at, timezone.utc).isoformat()
    record.update(status='interrupted', is_running=False, ended_at=ended, end_reason='legacy_import')
    record['events'].append({'id': str(uuid4()), 'session_id': record['id'], 'type': 'interrupted',
                             'timestamp': ended, 'reason': 'legacy_import'})


def summarize(record):
    domains = defaultdict(lambda: {'seconds': 0, 'visits': 0})
    for visit in record['website_visits']:
        domains[visit['domain']]['seconds'] += visit['duration_seconds']
        domains[visit['domain']]['visits'] += 1
    observed = sum(d['seconds'] for d in domains.values())
    known = record.get('duration_known', True)
    return {'id': record['id'], 'topic': record['topic'], 'status': record['status'],
            'startedAt': record['started_at'], 'endedAt': record['ended_at'],
            'summaryText': record.get('legacy_summary') or 'Imported recorded session and activity.',
            'plannedSeconds': record['planned_seconds'],
            'focusedSeconds': record['active_seconds'] if known else None,
            'pausedSeconds': record.get('paused_seconds') if known else None,
            'browserActiveSeconds': observed,
            'unattributedSeconds': max(0, record['active_seconds'] - observed) if known else None,
            'score': None, 'visitCount': len(record['website_visits']),
            'domains': [{'domain': domain, **value} for domain, value in domains.items()]}
