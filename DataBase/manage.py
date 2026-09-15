"""Offline profile provisioning and explicit legacy migration. Run with --help."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5
from DataBase.SessionRepository import SessionRepository, encode
from DataBase.LegacySessionAdapter import close_interrupted, summarize
from Settings.Settings import Settings


def migrate(repository, user_id, source):
    if user_id not in repository.users():
        raise ValueError('Create the owning profile before importing records')
    source = Path(source).resolve()
    raw = json.loads(source.read_text(encoding='utf-8'))
    with repository.connect() as db:
        previous = db.execute('SELECT user_id, payload, completed FROM legacy_imports WHERE source=?', (str(source),)).fetchone()
    if previous:
        if previous['user_id'] != user_id:
            raise ValueError('This legacy source is already assigned to another user')
        if json.loads(previous['payload']) != raw:
            raise ValueError('Legacy source changed after migration; review before importing a new snapshot')
        if previous['completed']:
            return 0
    if not isinstance(raw, dict):
        raise ValueError('Expected a legacy JSON object')
    records = raw.get('sessions', [])
    if 'website_visits' in raw and 'checkpoint' in raw:
        records = [raw]
    if 'session_info' in raw:
        records = [{**raw['session_info'], 'website_metadata': raw.get('website_metadata', [])}]
    if not records and 'website_metadata' not in raw and 'settings' not in raw and 'sessions' not in raw:
        raise ValueError('Unrecognized legacy format')
    # Reserve ownership before the first session transaction. A failed/partial
    # import can only be resumed for the same owner and unchanged source.
    if not previous:
        with repository.connect() as db:
            db.execute('INSERT INTO legacy_imports(source, user_id, payload, imported_at) VALUES (?, ?, ?, ?)',
                       (str(source), user_id, encode(raw), datetime.now(timezone.utc).isoformat()))
    for index, original in enumerate(records):
        if original.get('user_id') not in (None, user_id):
            raise ValueError('A legacy record belongs to a different user')
        record = deepcopy(original)
        identity = str(uuid5(NAMESPACE_URL, str(source) + ':' + str(index) + ':' + encode(original)))
        if 'website_visits' in record and 'checkpoint' in record:
            record['user_id'] = user_id
            if record['status'] in ('running', 'paused'):
                close_interrupted(record)
        else:
            visits = []
            for number, metadata in enumerate(record.get('website_metadata', [])):
                url = str(metadata.get('url', ''))
                try:
                    domain = urlsplit(url).hostname or ''
                except ValueError:
                    domain = ''
                block = metadata.get('block') if type(metadata.get('block')) is bool else None
                elapsed = metadata.get('time_spent', 0)
                elapsed = elapsed if type(elapsed) in (float, int) and elapsed >= 0 else 0
                visits.append({**metadata, 'id': str(uuid5(NAMESPACE_URL, identity + ':' + str(number))),
                               'session_id': identity, 'domain': domain, 'url': url,
                               'started_at': metadata.get('timestamp'), 'ended_at': None,
                               'duration_seconds': elapsed, 'block': block,
                               'decision': 'blocked' if block is True else 'allowed' if block is False else 'unknown'})
            record = {'id': identity, 'user_id': user_id, 'schema_version': 2,
                      'topic': str(original.get('topic') or 'Imported session'), 'status': 'legacy',
                      'is_running': False, 'started_at': str(original.get('start_time') or ''),
                      'ended_at': original.get('actual_end_time') or original.get('end_time'), 'planned_seconds': original.get('time') or 0,
                      'active_seconds': 0, 'paused_seconds': 0, 'longest_streak_seconds': 0,
                      'strict_mode': False, 'events': [], 'website_visits': visits,
                      'duration_known': False, 'legacy_record': original,
                      'legacy_summary': 'Imported prototype record. Session duration and complete activity accounting were not recorded; original metadata is preserved.'}
        repository.save_session(user_id, record, summarize(record))
    if 'settings' in raw:
        with repository.connect() as db:
            exists = db.execute('SELECT 1 FROM preferences WHERE user_id=?', (user_id,)).fetchone()
        if not exists:
            repository.save_preferences(user_id, {'settings': {**Settings.DEFAULTS, **raw['settings']},
                                                  'blocklist': raw.get('blocklist', [])})
    with repository.connect() as db:
        db.execute('UPDATE legacy_imports SET completed=1 WHERE source=? AND user_id=?', (str(source), user_id))
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', help='SQLite path (defaults to GROVE_SQL_PATH or DataBase/grove.sqlite3)')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('users', help='List profile IDs and names')
    create = commands.add_parser('create-user', help='Create a profile and print its access key once')
    create.add_argument('name')
    for name in ('issue-key', 'revoke-keys'):
        key = commands.add_parser(name)
        key.add_argument('user_id')
        key.add_argument('--role', choices=['user', 'ai'], default='user')
    migration = commands.add_parser('import-legacy', help='Assign/import legacy JSON; originals remain untouched')
    migration.add_argument('user_id')
    migration.add_argument('sources', nargs='+')
    args = parser.parse_args()
    repository = SessionRepository(args.database)
    if args.command == 'create-user':
        user_id, token = repository.create_user(args.name)
        print(f'User ID: {user_id}\nAccess key (keep private): {token}')
    elif args.command == 'issue-key':
        if args.user_id not in repository.users():
            parser.error('Unknown user ID')
        print(repository.issue_key(args.user_id, args.role))
    elif args.command == 'revoke-keys':
        with repository.connect() as db:
            db.execute('DELETE FROM access_keys WHERE user_id=? AND role=?', (args.user_id, args.role))
    elif args.command == 'users':
        with repository.connect() as db:
            for row in db.execute('SELECT id, name FROM users'):
                print(row['id'], row['name'])
    else:
        for source in args.sources:
            print(f'{source}: {migrate(repository, args.user_id, source)} sessions imported')


if __name__ == '__main__':
    main()
