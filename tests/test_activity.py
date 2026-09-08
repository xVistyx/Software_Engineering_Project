import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from UserSession.ActivityTracker import ActivityTracker
from System.System import System
from System.BackendRequests import BackendResponse


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'Activity.json'
        self.now = 1800000000.0
        self.tracker = ActivityTracker(self.path, clock=lambda: self.now)
        self.sequence = 0

    def call(self, action, **content):
        return self.tracker.handle(action, content)

    def start(self, minutes=10):
        self.session = self.call('start_session', topic='Research', minutes=minutes)
        return self.session['id']

    def observation(self, **patch):
        self.sequence += 1
        data = dict(event_id=str(self.sequence), session_id=self.session['id'], state='active',
                    reason='tab_activated', tab_id=1, window_id=1, url='https://example.com/article', title='Research')
        data.update(patch)
        return self.call('log_meta_data', **data)

    def summary(self):
        return self.call('get_session_summary', session_id=self.session['id'])

    def test_full_lifecycle_and_foreground_durations(self):
        sid = self.start()
        self.observation()
        self.now += 20
        self.observation(url='https://other.example/page', tab_id=2)
        self.now += 10
        self.call('update_session', session_id=sid, status='paused')
        self.now += 15
        self.assertFalse(self.observation()['stored'])
        self.call('update_session', session_id=sid, status='running')
        self.observation(url='https://other.example/page', tab_id=2)
        self.now += 5
        self.call('end_session', session_id=sid)
        summary = self.summary()
        self.assertEqual(summary['focusedSeconds'], 35)
        self.assertEqual(summary['pausedSeconds'], 15)
        self.assertEqual(summary['browserActiveSeconds'], 35)
        self.assertEqual(summary['pauseCount'], 1)
        self.assertEqual(summary['visitCount'], 3)
        self.assertEqual(summary['domains'][0]['seconds'], 20)
        details = self.call('get_session_details', session_id=sid)['session']
        self.assertEqual([e['type'] for e in details['events'] if e['type'] in ('started', 'paused', 'resumed', 'ended')], ['started', 'paused', 'resumed', 'ended'])
        self.assertTrue(all(v['session_id'] == sid and v['ended_at'] for v in details['website_visits']))
        self.assertIsNone(summary['score'])

    def test_metadata_outside_session_or_from_wrong_session_is_not_saved(self):
        self.assertFalse(self.call('log_meta_data', event_id='1', url='https://example.com')['stored'])
        self.start()
        self.assertFalse(self.observation(session_id='old-session')['stored'])
        self.assertEqual(self.summary()['visitCount'], 0)

    def test_idle_and_focus_loss_exclude_website_time(self):
        self.start()
        self.observation()
        self.now += 10
        self.observation(state='idle')
        self.now += 20
        self.observation(state='unfocused')
        self.now += 10
        self.observation()
        self.now += 5
        self.assertEqual(self.summary()['browserActiveSeconds'], 15)
        self.assertEqual(self.summary()['unattributedSeconds'], 30)

    def test_missing_heartbeat_caps_visit_and_reopens_after_gap(self):
        self.start()
        self.observation()
        self.now += 120
        self.tracker.checkpoint()
        self.assertEqual(self.summary()['browserActiveSeconds'], 45)
        self.observation()
        self.now += 5
        self.assertEqual(self.summary()['browserActiveSeconds'], 50)
        self.assertEqual(self.summary()['visitCount'], 2)

    def test_heartbeat_does_not_duplicate_visits(self):
        self.start()
        self.observation()
        for _ in range(3):
            self.now += 30
            self.observation(reason='heartbeat')
        self.assertEqual(self.summary()['browserActiveSeconds'], 90)
        self.assertEqual(self.summary()['visitCount'], 1)

    def test_duplicate_event_and_page_title_updates(self):
        self.start()
        self.observation(event_id='same')
        self.assertEqual(self.observation(event_id='same')['reason'], 'duplicate')
        self.observation(title='Updated title')
        details = self.call('get_session_details', session_id=self.session['id'])
        self.assertEqual(details['session']['website_visits'][0]['title'], 'Updated title')
        self.assertEqual(self.summary()['visitCount'], 1)

    def test_automatic_completion_without_popup(self):
        self.start(minutes=1)
        self.observation()
        self.now += 30
        self.observation()
        self.now += 60
        self.tracker.checkpoint()
        self.assertFalse(self.call('get_active_session')['is_running'])
        summary = self.summary()
        self.assertEqual(summary['status'], 'completed')
        self.assertEqual(summary['focusedSeconds'], 60)
        self.assertEqual(summary['browserActiveSeconds'], 60)
        self.call('end_session', session_id=self.session['id'])
        self.assertEqual(self.summary()['status'], 'completed')

    def test_restart_preserves_checkpoint_without_counting_offline_gap(self):
        sid = self.start()
        self.observation()
        self.now += 20
        self.tracker.checkpoint()
        self.now += 500
        self.tracker = ActivityTracker(self.path, clock=lambda: self.now)
        self.assertEqual(self.summary()['status'], 'interrupted')
        self.assertEqual(self.summary()['focusedSeconds'], 20)
        self.assertEqual(self.summary()['browserActiveSeconds'], 20)
        self.assertFalse(self.call('get_active_session')['is_running'])
        self.assertEqual(self.call('get_session_details', session_id=sid)['session']['end_reason'], 'backend_restart')

    def test_strict_mode_enforced_by_backend(self):
        self.call('update_settings', strictMode=True)
        sid = self.start(minutes=1)
        for action, patch in [('end_session', {}), ('update_session', {'status': 'paused'})]:
            with self.assertRaises(ValueError):
                self.call(action, session_id=sid, **patch)
        self.now += 60
        self.tracker.checkpoint()
        self.assertEqual(self.summary()['status'], 'completed')

    def test_validation_and_settings_persistence(self):
        for minutes in [0, -1, True, float('nan'), float('inf'), 1.5, '45', 481]:
            with self.assertRaises(ValueError):
                self.call('start_session', topic='Research', minutes=minutes)
        self.call('update_settings', defaultMinutes=75, sounds=True)
        self.call('update_blocklist', sites=['example.com', 'example.com'])
        with self.assertRaises(ValueError):
            self.call('update_settings', sounds=False, unknown=True)
        other = ActivityTracker(self.path, clock=lambda: self.now)
        self.assertTrue(other.handle('get_settings', {})['sounds'])
        self.assertEqual(other.handle('get_blocklist', {})['sites'], ['example.com'])

    def test_atomic_concurrent_requests_and_response_shapes(self):
        def start(_):
            try:
                return self.call('start_session', topic='Concurrent', minutes=1)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(start, range(8)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(json.loads(self.path.read_text())['sessions']), 1)
        system = System(self.tracker)
        for action in ['get_sessions', 'get_stats', 'get_settings', 'get_blocklist', 'export_activity']:
            result = system.buildResponse({'action': action, 'content': {}})
            self.assertIsInstance(system.send_requests_to_frontend(result), BackendResponse)

    def test_private_and_internal_urls_excluded(self):
        self.start()
        self.assertFalse(self.observation(incognito=True)['stored'])
        self.assertFalse(self.observation(url='edge://settings')['stored'])
        self.assertEqual(self.summary()['visitCount'], 0)


if __name__ == '__main__':
    unittest.main()
