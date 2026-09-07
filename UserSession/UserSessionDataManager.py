from interfaces import IDataManger
from datetime import datetime


class UserSessionDataManager:

    def __init__(self):
        self.global_data_manager: IDataManger | None = None
        self.session_table = "sessions"
        self.metadata_table = "website_metadata"

    def set_global_data_manager(self, data_manager: IDataManger):
        self.global_data_manager = data_manager

    def log_session_start(self, content: dict):

        if self.global_data_manager is None:
            raise RuntimeError("Global data manager has not been set")

        clean_session = {
            "id": content["id"],
            "topic": content["topic"],
            "is_running": content["is_running"],
            "time": content["time"],
            "start_time": content["start_time"].isoformat(),
            "last_update_time": content["last_update_time"].isoformat()
        }

        print("SENDING TO GLOBAL DB:", clean_session)

        self.global_data_manager.write_to_db(
            self.session_table,
            clean_session
        )

    def set_meta_data(self, metadata: dict):
        if self.global_data_manager is None:
            raise RuntimeError("Global data manager has not been set")

        metadata_data = {
            "tab_id": metadata.get("tab_id"),
            "title": metadata.get("title", ""),
            "url": metadata.get("url", ""),
            "favicon": metadata.get("favicon", ""),
            "timestamp": self._make_json_safe(
                metadata.get("timestamp")
            )
        }

        self.global_data_manager.write_to_db(
            self.metadata_table,
            metadata_data
        )

    def get_active_session(self):
        if self.global_data_manager is None:
            raise RuntimeError("Global data manager has not been set")

        sessions = self.global_data_manager.read_from_db(
            self.session_table
        )

        for session in reversed(sessions):
            if session.get("is_running") is True:
                return session

        return None

    def _make_json_safe(self, value):
        if isinstance(value, datetime):
            return value.isoformat()

        return value