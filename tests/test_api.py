"""Real HTTP checks, using only the existing runtime and Python standard library."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from DataBase.SessionRepository import SessionRepository


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        cls.repo = SessionRepository(root / 'test.sqlite3')
        cls.alice, cls.alice_key = cls.repo.create_user('Alice')
        cls.bob, cls.bob_key = cls.repo.create_user('Bob')
        cls.ai_key = cls.repo.issue_key(cls.alice, 'ai')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.log = (root / 'server.log').open('w')
        cls.addClassCleanup(cls.log.close)
        # Closing stdin stops Uvicorn gracefully, including behind Windows' venv launcher.
        server_script = '''
import sys
import threading
import uvicorn
server = uvicorn.Server(uvicorn.Config('main:app', host='127.0.0.1', port=int(sys.argv[1])))
def stop_on_eof():
    sys.stdin.read()
    server.should_exit = True
threading.Thread(target=stop_on_eof, daemon=True).start()
server.run()
'''
        cls.server = subprocess.Popen(
            [sys.executable, '-B', '-c', server_script, str(cls.port)],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, 'GROVE_SQL_PATH': str(cls.repo.path), 'GROVE_ACTIVITY_PATH': str(root / 'Activity.json')},
            stdin=subprocess.PIPE, stdout=cls.log, stderr=cls.log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            if cls.server.poll() is not None:
                raise RuntimeError((root / 'server.log').read_text())
            try:
                if cls.request('get_sessions', key=cls.alice_key)[0] == 200:
                    break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('Test backend did not start')

    @classmethod
    def stop_server(cls):
        try:
            cls.server.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(cls.server.pid), '/T', '/F'],
                               check=True, creationflags=subprocess.CREATE_NO_WINDOW,
                               stdout=cls.log, stderr=cls.log)
            else:
                cls.server.kill()
            cls.server.communicate(timeout=10)

    @classmethod
    def request(cls, action, content=None, key=None):
        headers = {'Content-Type': 'application/json'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        request = Request(f'http://127.0.0.1:{cls.port}/backend',
                          data=json.dumps({'action': action, 'content': content or {}}).encode(), headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_authentication_ownership_and_ai_round_trip(self):
        self.assertEqual(self.request('get_sessions')[0], 401)
        self.assertEqual(self.request('get_sessions', key='invalid')[0], 401)
        status, started = self.request('start_session', {'topic': 'HTTP session', 'minutes': 1}, self.alice_key)
        self.assertEqual(status, 200)
        sid = started['content']['id']
        for action in ('get_session_details', 'get_session_summary', 'end_session', 'update_session'):
            self.assertEqual(self.request(action, {'session_id': sid}, self.bob_key)[0], 404)
        self.assertEqual(self.request('get_sessions', key=self.bob_key)[1]['content'], [])
        self.assertEqual(self.request('get_sessions', {'user_id': self.alice}, self.bob_key)[0], 400)
        status, ended = self.request('end_session', {'session_id': sid}, self.alice_key)
        self.assertEqual(status, 200)
        self.assertEqual(ended['content']['storage_status'], 'saved')
        self.assertEqual(self.request('get_sessions', key=self.alice_key)[1]['content'],
                         self.request('get_past_sessions', key=self.alice_key)[1]['content'])
        self.assertEqual(self.request('export_activity', key=self.bob_key)[1]['content']['sessions'], [])
        self.assertEqual(self.request('get_ai_session', {'session_id': sid}, self.alice_key)[0], 403)
        self.assertEqual(self.request('start_session', {'topic': 'No', 'minutes': 1}, self.ai_key)[0], 403)
        status, data = self.request('get_ai_session', {'session_id': sid}, self.ai_key)
        self.assertEqual(status, 200)
        self.assertEqual(data['content']['session_info']['topic'], 'HTTP session')
        self.assertIn('website_metadata', data['content'])
        self.assertEqual(self.request('save_session_analysis', {'session_id': sid, 'analysis': {'summary': 'Reviewed'}}, self.ai_key)[0], 200)
        details = self.request('get_session_details', {'session_id': sid}, self.alice_key)[1]['content']
        self.assertEqual(details['analysis']['summary'], 'Reviewed')
        bob_ai = self.repo.issue_key(self.bob, 'ai')
        status, sessions = self.request('get_ai_sessions', key=self.ai_key)
        self.assertEqual(status, 200)
        self.assertEqual(sessions['content'][0]['id'], str(sid))
        self.assertEqual(set(sessions['content'][0]), {'id', 'topic', 'started_at'})
        self.assertEqual(self.request('get_ai_sessions', key=bob_ai)[1]['content'], [])
        self.assertEqual(self.request('get_ai_sessions', key=self.alice_key)[0], 403)
        self.assertEqual(self.request('get_ai_sessions', {'user_id': self.bob}, self.ai_key)[0], 400)
        self.assertEqual(self.request('get_ai_session', {'session_id': sid}, bob_ai)[0], 404)
        self.assertEqual(self.request('save_session_analysis', {'session_id': sid, 'analysis': {'summary': 'No'}}, bob_ai)[0], 404)
        with self.repo.connect() as db:
            db.execute('DELETE FROM access_keys WHERE user_id=?', (self.alice,))
        self.assertEqual(self.request('get_sessions', key=self.alice_key)[0], 401)


if __name__ == '__main__':
    unittest.main()
