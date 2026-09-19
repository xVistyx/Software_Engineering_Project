"""Transactional, user-scoped session archive. JSON columns retain the AI/export contract."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from uuid import uuid4


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


class SessionRepository:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('GROVE_SQL_PATH') or
                         Path(__file__).resolve().parent / 'grove.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 1:
                raise ValueError('This database requires a newer Grove backend')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS access_keys (
                    digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    role TEXT NOT NULL CHECK(role IN ('user', 'ai')));
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT PRIMARY KEY REFERENCES users(id), payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT NOT NULL REFERENCES users(id), id TEXT NOT NULL,
                    topic TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL,
                    ended_at TEXT, active_seconds REAL, summary TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(user_id, id));
                CREATE INDEX IF NOT EXISTS sessions_by_date ON sessions(user_id, started_at DESC);
                CREATE TABLE IF NOT EXISTS visits (
                    user_id TEXT NOT NULL, session_id TEXT NOT NULL, id TEXT NOT NULL,
                    domain TEXT, duration_seconds REAL, decision TEXT, payload TEXT NOT NULL,
                    PRIMARY KEY(user_id, session_id, id),
                    FOREIGN KEY(user_id, session_id) REFERENCES sessions(user_id, id));
                CREATE TABLE IF NOT EXISTS events (
                    user_id TEXT NOT NULL, session_id TEXT NOT NULL, id TEXT NOT NULL,
                    type TEXT, timestamp TEXT, payload TEXT NOT NULL,
                    PRIMARY KEY(user_id, session_id, id),
                    FOREIGN KEY(user_id, session_id) REFERENCES sessions(user_id, id));
                CREATE TABLE IF NOT EXISTS analyses (
                    user_id TEXT NOT NULL, session_id TEXT NOT NULL, payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL, PRIMARY KEY(user_id, session_id),
                    FOREIGN KEY(user_id, session_id) REFERENCES sessions(user_id, id));
                CREATE TABLE IF NOT EXISTS legacy_imports (
                    source TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    payload TEXT NOT NULL, imported_at TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0);
                PRAGMA user_version = 1;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def ensure_user(self, user_id, name=None):
        with self.connect() as db:
            db.execute('INSERT INTO users VALUES (?, ?) ON CONFLICT DO NOTHING', (user_id, name or user_id))

    def users(self):
        with self.connect() as db:
            return [row['id'] for row in db.execute('SELECT id FROM users')]

    def create_user(self, user_id, token):
        token_digest = hashlib.sha256(token.encode()).hexdigest()

        with self.connect() as db:
            db.execute(
                """
                INSERT INTO users (id, name)
                VALUES (?, ?)
                """,
                (user_id, user_id)
            )

            db.execute(
                """
                INSERT INTO access_keys (digest, user_id, role)
                VALUES (?, ?, ?)
                """,
                (token_digest, user_id, "user")
            )

    def issue_key(self, user_id, role='user'):
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO access_keys VALUES (?, ?, ?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user_id, role))
        return token

    def authenticate(self, token):
        token_digest = hashlib.sha256(token.encode()).hexdigest()

        with self.connect() as db:
            row = db.execute(
                """
                SELECT user_id, role
                FROM access_keys
                WHERE digest = ?
                """,
                (token_digest,)
            ).fetchone()

        if row is None:
            return None

        return {
            "user_id": row["user_id"],
            "role": row["role"]
        }

    def preferences(self, user_id, defaults):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM preferences WHERE user_id = ?', (user_id,)).fetchone()
            return json.loads(row['payload']) if row else {'settings': deepcopy(defaults), 'blocklist': []}

    def save_preferences(self, user_id, data):
        payload = encode({key: data[key] for key in ('settings', 'blocklist')})
        with self.connect() as db:
            db.execute('INSERT INTO preferences VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload',
                       (user_id, payload))

    def save_session(self, user_id, session, summary):
        if session.get('user_id') != user_id or session['status'] in ('running', 'paused'):
            raise ValueError('Only finished sessions owned by this user can be archived')
        record = deepcopy(session)
        record.pop('activity_event_ids', None)
        # The first complete archive is immutable. A retry after commit is a no-op,
        # including retries after a crash between commit and spool deletion.
        with self.connect() as db:
            inserted = db.execute('''INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, id) DO NOTHING''',
                (user_id, record['id'], record['topic'], record['status'], record['started_at'],
                 record['ended_at'], record['active_seconds'] if record.get('duration_known', True) else None,
                 encode(summary), encode(record))).rowcount
            if not inserted:
                if 'source_summary' in record:
                    previous = db.execute('SELECT payload FROM sessions WHERE user_id=? AND id=?',
                                          (user_id, record['id'])).fetchone()
                    if json.loads(previous['payload']).get('source_summary') != record['source_summary']:
                        raise ValueError('A different summary already uses this session ID')
                return
            for visit in record['website_visits']:
                db.execute('INSERT INTO visits VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (user_id, record['id'], visit['id'], visit.get('domain'),
                            visit.get('duration_seconds'), visit.get('decision'), encode(visit)))
            for event in record['events']:
                db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)',
                           (user_id, record['id'], event['id'], event['type'], event['timestamp'], encode(event)))

    def get(self, user_id, session_id):
        with self.connect() as db:
            row = db.execute('''SELECT s.payload, s.summary, a.payload AS analysis FROM sessions s
                LEFT JOIN analyses a ON s.user_id=a.user_id AND s.id=a.session_id
                WHERE s.user_id=? AND s.id=?''', (user_id, session_id)).fetchone()
        if row is None:
            raise ValueError('Session not found')
        return {'session': json.loads(row['payload']), 'summary': json.loads(row['summary']),
                'analysis': json.loads(row['analysis']) if row['analysis'] else None,
                'storage_status': 'saved'}

    def list(self, user_id):
        with self.connect() as db:
            return [json.loads(row['payload']) for row in db.execute(
                'SELECT payload FROM sessions WHERE user_id=? ORDER BY started_at DESC, id', (user_id,))]

    def save_analysis(self, user_id, session_id, analysis):
        self.get(user_id, session_id)
        if not isinstance(analysis, dict) or not isinstance(analysis.get('summary'), str) or not analysis['summary'].strip():
            raise ValueError('Analysis requires a nonempty summary string')
        if len(encode(analysis)) > 100_000:
            raise ValueError('Analysis is too large')
        with self.connect() as db:
            db.execute('''INSERT INTO analyses VALUES (?, ?, ?, ?) ON CONFLICT(user_id, session_id)
                DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at''',
                (user_id, session_id, encode(analysis), datetime.now(timezone.utc).isoformat()))
        return {'saved': True, 'session_id': session_id}

    def legacy_sources(self, user_id):
        with self.connect() as db:
            return [json.loads(row['payload']) for row in db.execute(
                'SELECT payload FROM legacy_imports WHERE user_id=?', (user_id,))]

    def ai_input(self, user_id, session_id):
        data = self.get(user_id, session_id)
        session = data['session']
        # Preserve the team's temporary-session envelope and website metadata names.
        return {'schema_version': 1, 'session_id': session_id, 'user_id': user_id,
                'session_info': {k: v for k, v in session.items() if k not in ('website_visits', 'events')},
                'summary': data['summary'], 'events': session['events'],
                'website_metadata': [{**v, 'timestamp': v.get('started_at'),
                                      'time_spent': v.get('duration_seconds'),
                                      'block': v.get('block'), 'is_related': v.get('is_related')}
                                     for v in session['website_visits']]}