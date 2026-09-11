"""Persistent session timelines and bounded, foreground website observations."""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4


def stamp(seconds):
    """
    This function is responsible for getting a current time stamp
    Used soley for the getting accurate time readings for the time stamps
    """
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class ActivityTracker:
    HEARTBEAT_TTL = 45
    DEFAULTS = {"defaultMinutes": 45, "breakReminders": True, "sounds": False, "strictMode": False}

    def __init__(self, path=None, clock=None):
        self.path = Path(path or os.environ.get('GROVE_ACTIVITY_PATH') or Path(__file__).resolve().parents[1] / 'DataBase' / 'Activity.json')
        self.clock = clock or (lambda: datetime.now(timezone.utc).timestamp())
        self.lock = RLock()
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
            "schema_version": 1, "settings": dict(self.DEFAULTS), "blocklist": [], "sessions": []
        }
        # A process restart cannot establish what happened while it was offline.
        # Preserve the checkpoint, close the visit there, and require a new session.
        recovered = False
        for session in self.data['sessions']:
            if session['status'] in ('running', 'paused'):
                at = session['checkpoint']
                self._close_visit(session, at, 'backend_restart')
                session.update(status='interrupted', is_running=False, ended_at=stamp(at), end_reason='backend_restart')
                self._event(session, 'interrupted', at, detected_at=stamp(self.clock()), reason='backend_restart')
                recovered = True
        if recovered:
            self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def _event(self, session, kind, at, **details):
        session['events'].append({"id": str(uuid4()), "session_id": session['id'], "type": kind, "timestamp": stamp(at), **details})

    def _active(self):
        return next((s for s in reversed(self.data['sessions']) if s['status'] in ('running', 'paused')), None)

    def _find(self, session_id):
        session = next((s for s in self.data['sessions'] if s['id'] == session_id), None)
        if session is None:
            raise ValueError('Session not found')
        return session

    def _visit(self, session):
        visits = session['website_visits']
        return visits[-1] if visits and visits[-1]['ended_at'] is None else None

    def _accrue_visit(self, session, at):
        visit = self._visit(session)
        if visit:
            until = min(at, visit['last_seen_epoch'] + self.HEARTBEAT_TTL)
            visit['duration_seconds'] += max(0, until - visit['accounted_at'])
            visit['accounted_at'] = max(visit['accounted_at'], until)

    def _close_visit(self, session, at, reason):
        self._accrue_visit(session, at)
        visit = self._visit(session)
        if visit:
            end = min(at, visit['last_seen_epoch'] + self.HEARTBEAT_TTL)
            visit.update(ended_at=stamp(end), end_reason=reason)

    def _advance(self, at):
        session = self._active()
        if not session:
            return
        at = max(at, session['checkpoint'])
        elapsed = at - session['checkpoint']
        if session['status'] == 'running':
            counted = min(elapsed, session['planned_seconds'] - session['active_seconds'])
            until = session['checkpoint'] + counted
            session['active_seconds'] += counted
            session['current_streak_seconds'] += counted
            session['longest_streak_seconds'] = max(session['longest_streak_seconds'], session['current_streak_seconds'])
            self._accrue_visit(session, until)
            visit = self._visit(session)
            if visit and until > visit['last_seen_epoch'] + self.HEARTBEAT_TTL:
                expired = visit['last_seen_epoch'] + self.HEARTBEAT_TTL
                self._close_visit(session, expired, 'tracking_gap')
                self._event(session, 'tracking_gap', expired)
            session['checkpoint'] = until
            if session['active_seconds'] >= session['planned_seconds']:
                self._finish(session, until, 'timer_finished')
        else:
            session['paused_seconds'] += elapsed
            session['checkpoint'] = at

    def _finish(self, session, at, reason):
        self._close_visit(session, at, reason)
        status = 'completed' if reason == 'timer_finished' else 'ended'
        session.update(status=status, is_running=False, ended_at=stamp(at), end_reason=reason, checkpoint=at)
        self._event(session, status, at, reason=reason)

    def checkpoint(self):
        with self.lock:
            if self._active():
                previous = deepcopy(self.data)
                try:
                    self._advance(self.clock())
                    self._save()
                except Exception:
                    self.data = previous
                    raise

    def _public(self, session):
        remaining = max(0, math.ceil(session['planned_seconds'] - session['active_seconds']))
        return {"id": session['id'], "topic": session['topic'], "status": session['status'],
                "is_running": session['status'] == 'running', "minutes": session['planned_seconds'] / 60,
                "time": remaining, "time_remaining": remaining, "start_time": session['started_at'],
                "strict_mode": session['strict_mode']}

    def _summary(self, session):
        domains = defaultdict(lambda: {"seconds": 0, "visits": 0})
        for visit in session['website_visits']:
            domains[visit['domain']]['seconds'] += visit['duration_seconds']
            domains[visit['domain']]['visits'] += 1
        observed = sum(item['seconds'] for item in domains.values())
        return {"id": session['id'], "topic": session['topic'], "status": session['status'],
                "startedAt": session['started_at'], "endedAt": session['ended_at'],
                "plannedSeconds": session['planned_seconds'], "focusedSeconds": round(session['active_seconds'], 3),
                "pausedSeconds": round(session['paused_seconds'], 3), "browserActiveSeconds": round(observed, 3),
                "unattributedSeconds": round(max(0, session['active_seconds'] - observed), 3),
                "pauseCount": sum(e['type'] == 'paused' for e in session['events']),
                "visitCount": len(session['website_visits']), "uniqueDomains": len(domains),
                "longestStreakMin": round(session['longest_streak_seconds'] / 60, 2),
                "score": None, "tabsBlocked": 0, "driftCount": None,
                "domains": [{"domain": domain, "seconds": round(data['seconds'], 3), "visits": data['visits']}
                            for domain, data in sorted(domains.items(), key=lambda item: -item[1]['seconds'])]}

    def _observe(self, content, at):
        session = self._active()
        if not session or session['status'] != 'running' or content.get('session_id') != session['id']:
            return {"stored": False, "reason": "no_matching_running_session"}
        event_id = str(content.get('event_id', ''))[:100]
        if not event_id:
            raise ValueError('An activity event_id is required')
        if event_id in session['activity_event_ids']:
            return {"stored": False, "reason": "duplicate"}
        session['activity_event_ids'] = (session['activity_event_ids'] + [event_id])[-256:]
        state = content.get('state', 'active')
        if state not in ('active', 'idle', 'locked', 'unfocused', 'unsupported', 'closed'):
            raise ValueError('Invalid activity state')
        reason = str(content.get('reason', 'observation'))[:80]
        if state != session.get('browser_state'):
            self._event(session, 'browser_state', at, state=state, reason=reason,
                        client_timestamp=str(content.get('timestamp', ''))[:80])
            session['browser_state'] = state
        if state != 'active':
            self._close_visit(session, at, state)
            return {"stored": True}
        parts = urlsplit(str(content.get('url', ''))[:8192])
        if parts.scheme not in ('http', 'https') or not parts.hostname or content.get('incognito'):
            self._close_visit(session, at, 'unsupported')
            return {"stored": False, "reason": "unsupported_url"}
        # Retain paths and query strings for analysis; omit credentials/fragments.
        host = parts.hostname.lower()
        authority = ('[' + host + ']') if ':' in host else host
        if parts.port:
            authority += ':' + str(parts.port)
        url = urlunsplit((parts.scheme, authority, parts.path, parts.query, ''))
        title = str(content.get('title', ''))[:1000]
        visit = self._visit(session)
        if visit and (visit['url'], visit['tab_id'], visit['window_id']) == (url, content.get('tab_id'), content.get('window_id')):
            if title != visit['title']:
                self._event(session, 'title_changed', at, visit_id=visit['id'], title=title)
            visit.update(title=title, last_seen_at=stamp(at), last_seen_epoch=at,
                         observation_count=visit['observation_count'] + 1)
            return {"stored": True, "visit_id": visit['id']}
        self._close_visit(session, at, reason)
        visit = {"id": str(uuid4()), "session_id": session['id'], "tab_id": content.get('tab_id'),
                 "window_id": content.get('window_id'), "url": url, "domain": host, "title": title,
                 "favicon": str(content.get('favicon', ''))[:4096], "audible": bool(content.get('audible')),
                 "pinned": bool(content.get('pinned')), "started_at": stamp(at), "ended_at": None,
                 "last_seen_at": stamp(at), "last_seen_epoch": at, "accounted_at": at,
                 "duration_seconds": 0, "observation_count": 1, "start_reason": reason, "end_reason": None}
        session['website_visits'].append(visit)
        self._event(session, 'website_entered', at, visit_id=visit['id'], reason=reason,
                    client_timestamp=str(content.get('timestamp', ''))[:80])
        return {"stored": True, "visit_id": visit['id']}

    def handle(self, action, content):
        with self.lock:
            previous = deepcopy(self.data)
            try:
                at = self.clock()
                self._advance(at)
                result = self._handle(action, content, at)
                if self.data != previous:
                    self._save()
                return deepcopy(result)
            except Exception:
                self.data = previous
                raise

    def _handle(self, action, content, at):
        if action == 'get_active_session':
            active = self._active()
            return self._public(active) if active else {"is_running": False}
        if action == 'start_session':
            if self._active():
                raise ValueError('End the current session before starting another')
            topic = content.get('topic')
            minutes = content.get('minutes')
            if not isinstance(topic, str) or not topic.strip() or len(topic) > 160:
                raise ValueError('A topic of 1 to 160 characters is required')
            if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not math.isfinite(minutes) or not 1 <= minutes <= 480 or minutes != int(minutes):
                raise ValueError('Duration must be a whole number from 1 to 480 minutes')
            session = {"id": str(uuid4()), "schema_version": 1, "topic": topic.strip(),
                       "status": 'running', "is_running": True, "planned_seconds": int(minutes * 60),
                       "active_seconds": 0, "paused_seconds": 0, "current_streak_seconds": 0,
                       "longest_streak_seconds": 0, "started_at": stamp(at), "ended_at": None,
                       "end_reason": None, "checkpoint": at, "strict_mode": self.data['settings']['strictMode'],
                       "events": [], "website_visits": [], "activity_event_ids": [], "browser_state": None}
            self._event(session, 'started', at, planned_seconds=session['planned_seconds'])
            self.data['sessions'].append(session)
            return self._public(session)
        if action in ('update_session', 'end_session'):
            session = self._find(content.get('session_id'))
            if session['status'] not in ('running', 'paused'):
                return self._public(session)
            if session['strict_mode']:
                raise ValueError('Strict sessions cannot be paused or ended early')
            if action == 'end_session':
                self._finish(session, at, 'user_ended')
            else:
                status = content.get('status')
                if status not in ('paused', 'running'):
                    raise ValueError('Session status must be paused or running')
                if session['status'] != status:
                    self._close_visit(session, at, status)
                    self._event(session, 'paused' if status == 'paused' else 'resumed', at)
                    session.update(status=status, is_running=status == 'running', checkpoint=at,
                                   current_streak_seconds=0, browser_state=None)
            return self._public(session)
        if action == 'log_meta_data':
            return self._observe(content, at)
        if action in ('get_session_summary', 'get_session_details'):
            session = self._find(content.get('session_id'))
            summary = self._summary(session)
            if action == 'get_session_summary':
                return summary
            result = deepcopy(session)
            result.pop('activity_event_ids', None)
            return {"session": result, "summary": summary}
        if action == 'get_sessions':
            return [{**self._public(s), "minutes": round(s['active_seconds'] / 60, 1),
                     "score": None, "ended_at": s['ended_at'], "visit_count": len(s['website_visits'])}
                    for s in reversed(self.data['sessions'])]
        if action == 'export_activity':
            sessions = deepcopy(self.data['sessions'])
            for session in sessions:
                session.pop('activity_event_ids', None)
            return {"schema_version": 1, "exported_at": stamp(at), "sessions": sessions,
                    "notes": "Times are UTC. Session time is not a measurement of attention. Website duration is bounded by foreground observations and a 45-second heartbeat timeout."}
        if action == 'get_stats':
            sessions = self.data['sessions']
            now = datetime.fromtimestamp(at, timezone.utc)
            monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            return {"total": len(sessions), "thisWeek": sum(s['started_at'] >= monday for s in sessions),
                    "focusedHours": round(sum(s['active_seconds'] for s in sessions) / 3600, 1),
                    "peakDriftHour": '—', "trackedSites": len({v['domain'] for s in sessions for v in s['website_visits']})}
        if action == 'get_settings':
            return self.data['settings']
        if action == 'update_settings':
            for key, value in content.items():
                if key not in self.DEFAULTS:
                    raise ValueError('Unknown setting')
                if key == 'defaultMinutes':
                    if type(value) is not int or not 1 <= value <= 480:
                        raise ValueError('Invalid default duration')
                elif type(value) is not bool:
                    raise ValueError('Settings switches require a boolean')
            self.data['settings'].update(content)
            return self.data['settings']
        if action == 'get_blocklist':
            return {"sites": self.data['blocklist']}
        if action == 'update_blocklist':
            sites = content.get('sites')
            if not isinstance(sites, list) or len(sites) > 500 or any(not isinstance(s, str) or not s or len(s) > 253 for s in sites):
                raise ValueError('Invalid blocklist')
            self.data['blocklist'] = list(dict.fromkeys(sites))
            return {"sites": self.data['blocklist']}
        raise ValueError('Unknown action')
