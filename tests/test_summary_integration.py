from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from DataBase.DataBaseManager import DataBaseManager
from DataBase.SessionRepository import SessionRepository
from DataBase.manage import migrate
from System.System import System
from UserSession.StopSession.GenerateSummary import SessionSummaryForDB


class SummaryIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.repo = SessionRepository(self.root / 'test.sqlite3')
        self.alice, self.key = self.repo.create_user('Alice')
        self.bob, self.other_key = self.repo.create_user('Bob')
        self.db = DataBaseManager(self.repo)
        self.now = datetime(2026, 9, 15, 12)
        self.restart()

    def restart(self):
        self.system = System(db_manager=self.db, activity_path=self.root / 'Activity.json', clock=lambda: self.now)
        self.manager = self.system.for_user(self.alice)

    def call(self, action, **content):
        return self.system.handle_request({'action': action, 'content': content},
                                         self.system.authenticate(self.key)).content

    def start(self):
        sid = self.call('start_session', topic='Team summary', minutes=1)['id']
        self.now += timedelta(seconds=20)
        return sid

    def files(self):
        return list(self.manager.user_session_data_manager.session_folder.glob('session_*.json'))

    def test_exact_colleague_dataclass_round_trip_and_isolation(self):
        dto = SessionSummaryForDB(123456, 'Supplied topic', self.now, self.now + timedelta(seconds=30),
                                  60.0, 30.0, 20.0, 67, 3, 25, 'Reference page', 'social.test')
        for _ in range(2):
            self.db.save_session(self.alice, dto)
        stored = self.db.get_session_details(self.alice, '123456')
        expected = asdict(dto)
        for key in ('session_start_time', 'session_end_time'):
            expected[key] = expected[key].isoformat()
        self.assertEqual(stored['session']['source_summary'], expected)
        self.assertEqual(stored['summary']['score'], 67)
        self.assertEqual(stored['session']['detail_level'], 'summary')
        self.assertIsNone(stored['summary']['pausedSeconds'])
        self.assertEqual(len(self.db.get_history(self.alice)), 1)
        self.assertEqual(self.db.get_history(self.bob), [])
        with self.assertRaisesRegex(ValueError, 'Session not found'):
            self.db.get_session_details(self.bob, '123456')

    def test_successful_stop_saves_then_session_manager_deletes(self):
        sid = self.start()
        original_save = self.db.save_session
        original_delete = self.manager.delete_old_session
        calls = []
        def save(owner, dto):
            self.assertIsInstance(dto, SessionSummaryForDB)
            self.assertTrue(self.files())
            original_save(owner, dto)
            self.assertTrue(self.files())
            calls.append('committed')
        def delete(session_id):
            self.assertEqual(calls, ['committed'])
            original_delete(session_id)
            calls.append('deleted')
        with patch.object(self.db, 'save_session', save), patch.object(self.manager, 'delete_old_session', delete):
            self.assertEqual(self.call('end_session', session_id=sid)['storage_status'], 'saved')
        self.assertEqual(calls, ['committed', 'deleted'])
        self.assertEqual(self.files(), [])
        details = self.call('get_session_details', session_id=sid)
        self.assertEqual(details['session']['source_summary']['actual_session_duration'], 20)
        self.assertEqual(self.call('get_sessions'), self.call('get_past_sessions'))
        self.restart()
        self.assertEqual(self.call('get_session_details', session_id=sid), details)

    def test_failed_sql_save_retains_data_and_retry_is_idempotent(self):
        sid = self.start()
        with patch.object(self.db, 'save_session', side_effect=sqlite3.OperationalError('full')):
            with self.assertLogs(level='ERROR'):
                result = self.call('end_session', session_id=sid)
                self.system.checkpoint()
            self.assertEqual(result['storage_status'], 'pending')
            self.assertEqual(len(self.files()), 1)
            raw = json.loads(self.files()[0].read_text())
            self.assertFalse(raw['session_info']['is_running'])
            self.assertEqual(raw['summary_for_db']['actual_session_duration'], 20)
            self.assertEqual(self.db.get_history(self.alice), [])
        self.now += timedelta(hours=1)
        self.assertEqual(self.call('retry_session_saves')['pending'], 0)
        self.call('end_session', session_id=sid)
        self.call('retry_session_saves')
        self.assertEqual(len(self.db.get_history(self.alice)), 1)
        self.assertEqual(self.files(), [])
        self.assertEqual(self.call('get_session_summary', session_id=sid)['focusedSeconds'], 20)

    def test_restart_replays_frozen_summary_without_offline_time(self):
        sid = self.start()
        with patch.object(self.db, 'save_session', side_effect=OSError('disk')):
            with self.assertLogs(level='ERROR'):
                self.call('end_session', session_id=sid)
        frozen = json.loads(self.files()[0].read_text())['summary_for_db']
        self.now += timedelta(days=1)
        self.restart()
        self.assertEqual(self.db.get_session_details(self.alice, str(sid))['session']['source_summary'], frozen)
        self.assertEqual(self.files(), [])

    def test_cleanup_failure_retry_preserves_analysis_and_no_duplicates(self):
        sid = self.start()
        with patch.object(self.manager, 'delete_old_session', side_effect=PermissionError('locked')):
            with self.assertLogs(level='ERROR'):
                self.call('end_session', session_id=sid)
        self.repo.save_analysis(self.alice, str(sid), {'summary': 'Fixture analysis'})
        self.restart()
        self.assertEqual(self.files(), [])
        self.assertEqual(len(self.db.get_history(self.alice)), 1)
        self.assertEqual(self.call('get_session_details', session_id=sid)['analysis']['summary'], 'Fixture analysis')

    def test_temporary_write_failure_does_not_delete_or_save(self):
        sid = self.start()
        with patch('UserSession.UserSessionDataManager.os.replace', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.call('end_session', session_id=sid)
        self.assertTrue(self.files())
        self.assertTrue(self.manager.active_session['is_running'])
        self.assertEqual(self.db.get_history(self.alice), [])
        self.call('end_session', session_id=sid)
        self.assertEqual(self.files(), [])

    def test_summary_spool_failure_recovered_at_frozen_end_time(self):
        sid = self.start()
        with patch.object(self.manager.user_session_data_manager, 'save_pending_summary', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.call('end_session', session_id=sid)
        self.assertFalse(self.manager.active_session['is_running'])
        self.now += timedelta(hours=4)
        self.restart()
        self.assertEqual(self.call('get_session_summary', session_id=sid)['focusedSeconds'], 20)

    def test_restart_of_unfinished_work_uses_checkpoint(self):
        sid = self.start()
        self.system.checkpoint()
        self.now += timedelta(hours=4)
        self.restart()
        self.assertFalse(self.call('get_active_session')['is_running'])
        self.assertEqual(self.call('get_session_summary', session_id=sid)['focusedSeconds'], 20)

    def test_timer_completion_and_pause_resume(self):
        sid = self.start()
        self.call('update_session', session_id=sid, status='paused')
        self.now += timedelta(seconds=10)
        self.assertEqual(self.call('get_active_session')['status'], 'paused')
        self.call('update_session', session_id=sid, status='running')
        self.now += timedelta(seconds=45)
        self.system.checkpoint()
        self.assertFalse(self.call('get_active_session')['is_running'])
        self.assertEqual(self.files(), [])
        # The teammate's actual duration is wall time, including the pause.
        self.assertEqual(self.call('get_session_summary', session_id=sid)['focusedSeconds'], 70)

    def test_stop_with_website_activity_flushes_last_tab(self):
        sid = self.start()
        with patch('UserSession.MetadataProcessing.TabTimer.monotonic', return_value=100):
            self.call('log_meta_data', session_id=sid, tab_id=1, reason='tab_activated', state='active',
                      url='https://example.test', title='Reference', timestamp=self.now.isoformat())
        with patch('UserSession.MetadataProcessing.TabTimer.monotonic', return_value=108):
            result = self.call('end_session', session_id=sid)
        self.assertEqual(result['tabsOpened'], 1)
        summary = self.call('get_session_summary', session_id=sid)
        self.assertEqual(summary['browserActiveSeconds'], 8)
        self.assertEqual(summary['mostUsedTab'], 'Reference')
        self.assertEqual(self.files(), [])

    def test_duplicate_id_with_different_summary_is_rejected(self):
        sid = self.start()
        self.call('end_session', session_id=sid)
        raw = deepcopy(self.db.get_session_details(self.alice, str(sid))['session']['source_summary'])
        raw['session_topic'] = 'Different record'
        with self.assertRaisesRegex(ValueError, 'different summary'):
            self.db.save_session(self.alice, raw)
        self.assertEqual(self.db.get_history(self.alice)[0]['topic'], 'Team summary')

    def test_settings_failures_cannot_undo_archive_and_strict_mode_is_enforced(self):
        sid = self.start()
        self.now += timedelta(minutes=1)
        with patch.object(self.db, 'save_preferences', side_effect=sqlite3.OperationalError('locked')):
            with self.assertRaises(sqlite3.OperationalError):
                self.call('update_settings', strictMode=True)
        self.assertFalse(self.call('get_active_session')['is_running'])
        self.assertEqual(self.files(), [])
        self.call('update_settings', strictMode=True)
        sid = self.start()
        with self.assertRaises(ValueError):
            self.call('end_session', session_id=sid, _timer_finished=True)

    def test_legacy_migration_and_existing_sql_remain_readable(self):
        source = self.root / 'Db.json'
        source.write_text(json.dumps({'sessions': [{'id': 8, 'topic': 'Legacy', 'time': 60}]}))
        original = source.read_bytes()
        self.assertEqual(migrate(self.repo, self.alice, source), 1)
        self.assertEqual(migrate(self.repo, self.alice, source), 0)
        self.assertEqual(source.read_bytes(), original)
        self.restart()
        session = self.call('get_past_sessions')[0]
        self.assertEqual(session['topic'], 'Legacy')
        self.assertFalse(session['duration_known'])
        self.assertEqual(len(self.call('export_activity')['legacy_sources']), 1)
        with self.assertRaisesRegex(ValueError, 'another user'):
            migrate(self.repo, self.bob, source)


if __name__ == '__main__':
    unittest.main()
