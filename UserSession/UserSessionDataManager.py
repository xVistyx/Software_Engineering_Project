"""Temporary session JSON only. Permanent storage is owned by DataBaseManager."""
from datetime import datetime
from pathlib import Path
import json
import os


class UserSessionDataManager:
    def __init__(self, session_folder=None):
        self.session_folder = Path(session_folder or Path(__file__).resolve().parent / 'ActiveSessionDB')
        self.session_path = None

    def _path(self, session_id):
        if not str(session_id).isdigit():
            raise ValueError('Invalid session ID')
        return self.session_folder / f'session_{session_id}.json'

    def _write(self, path, data):
        self.session_folder.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.json.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, allow_nan=False, default=self._make_json_safe)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    def _make_json_safe(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f'Unsupported temporary value: {type(value).__name__}')

    def create_session_json(self, session_id):
        self.session_path = self._path(session_id)
        if self.session_path.exists():
            raise ValueError('Session ID already has temporary data')
        self._write(self.session_path, {'session_info': {}, 'website_metadata': []})
        return self.session_path

    def log_session_start(self, content):
        data = self.session_end_json(content['id'])
        data['session_info'] = content
        data['session_info']['tab_count'] = len(data['website_metadata'])
        self._write(self._path(content['id']), data)

    def write_metadata_to_session_json(self, metadata):
        data = json.loads(self.session_path.read_text(encoding='utf-8'))
        existing = next((i for i, item in enumerate(data['website_metadata'])
                         if item['tab_id'] == metadata['tab_id']), None)
        if existing is None:
            data['website_metadata'].append(metadata)
            data['session_info']['tab_count'] = len(data['website_metadata'])
        else:
            data['website_metadata'][existing] = metadata
        self._write(self.session_path, data)

    def update_metadata_in_session_json(self, metadata):
        self.write_metadata_to_session_json(metadata)
        return True

    def session_end_json(self, session_id):
        return json.loads(self._path(session_id).read_text(encoding='utf-8'))

    def save_pending_summary(self, session_id, summary, frontend):
        data = self.session_end_json(session_id)
        data['summary_for_db'] = summary
        data['frontend_summary'] = frontend
        self._write(self._path(session_id), data)

    def retained_sessions(self):
        for path in sorted(self.session_folder.glob('session_*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            if not data.get('session_info'):
                continue  # Failed start before any session metadata was written.
            if path != self._path(data['session_info']['id']):
                raise ValueError('Temporary session ID mismatch')
            yield data

    def delete_current_session_json(self, session_id=None):
        path = self._path(session_id) if session_id is not None else self.session_path
        if path is None:
            raise RuntimeError('No session selected for cleanup')
        path.unlink(missing_ok=True)
        if self.session_path == path:
            self.session_path = None
