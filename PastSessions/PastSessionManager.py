from interfaces import IPastSessionManager

class PastSessionManager(IPastSessionManager):
    def present(self, action, sessions, pending_ids, legacy_sources, now):
        """Render data supplied by System; this component has no database access."""
        if action in ('get_sessions', 'get_past_sessions'):
            return [{'id': s['id'], 'topic': s['topic'], 'start_time': s['started_at'],
                     'ended_at': s['ended_at'], 'minutes': s['active_seconds'] / 60,
                     'status': s['status'], 'duration_known': s.get('duration_known', True),
                     'score': s.get('source_summary', {}).get('session_score'),
                     'storage_status': 'pending' if s['id'] in pending_ids else 'saved'} for s in sessions]
        if action == 'export_activity':
            return {'schema_version': 2, 'exported_at': now.isoformat(), 'sessions': sessions,
                    'legacy_sources': legacy_sources,
                    'notes': 'New records retain SessionSummaryForDB only; detailed visits/events are unavailable. Durations are seconds. Source timestamps are preserved.'}
        if action == 'get_stats':
            from datetime import timedelta
            monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            return {'total': len(sessions), 'thisWeek': sum(s['started_at'] >= monday for s in sessions),
                    'focusedHours': round(sum(s['active_seconds'] for s in sessions) / 3600, 1), 'peakDriftHour': None}
        raise ValueError('Unknown history action')
    def __init__(self):
        self.test_dict = {"action": "start_session","content": {"id": "test-session-123"}}

    def past_session_manager(self, action: str, content: dict):
            if action == "get_sessions":
                return {
                     "action": action,
                    "content": []
                        }
            
            elif action == "get_stats":
                return {
                    "action": action,
                    "content": {
                            "total": 0,
                            "thisWeek": 0,
                            "focusedHours": 0,
                            "peakDriftHour": "-"
                                }
                        }
            
            elif action == "get_session_summary":
                            return {
                                "action": action,
                                "content": {
                                    "id": content.get("session_id"),
                                    "score": 0,
                                    "minutes": 0
                                }
                            }
            return self.test_dict
    
    
