from interfaces import IDataManger
from datetime import datetime
from pathlib import Path
import json


class UserSessionDataManager:

    def __init__(self):
        self.global_data_manager: IDataManger | None = None
        self.session_table = "sessions"
        self.metadata_table = "website_metadata"

        self.session_folder = Path("UserSession/ActiveSessionDB")
        self.session_folder.mkdir(parents=True, exist_ok=True)

        self.session_path: Path | None = None

    def set_global_data_manager(self, data_manager: IDataManger):
        self.global_data_manager = data_manager

    def create_session_json(self, session_id: int):
        self.session_path = (
            self.session_folder / f"session_{session_id}.json"
        )

        session_data = {
            "session_info": {},
            "website_metadata": []
        }

        self.session_path.write_text(
            json.dumps(session_data, indent=4)
        )

        return self.session_path

    def generate_summary(self):
        """Generates summary which will be logged in the DB."""
        ...

    def end_session(self):
        ...

    def log_session_start(self, content: dict):

        #self.create_session_json(content["id"])

        clean_session = {
            "id": content["id"],
            "topic": content["topic"],
            "is_running": content["is_running"],
            "time": content["time"],

            "start_time": content["start_time"].isoformat(),
            "last_update_time": content["last_update_time"].isoformat(),
            "predicted_end_time": content["predicted_end_time"].isoformat(),

            "actual_end_time": (
                content["actual_end_time"].isoformat()
                if content["actual_end_time"] is not None
                else None
            ),

            "blocked_tabs": content["blocked_tabs"],
            "tab_count": content["tab_count"],
            "complete_session": content["complete_session"]
        }

        database = json.loads(
            self.session_path.read_text()
        )

        database["session_info"] = clean_session

        self.session_path.write_text(
            json.dumps(database, indent=4)
        )

    def write_metadata_to_session_json(self, data: dict):

        if self.session_path is None:
            raise RuntimeError("No active session JSON has been created.")

        database = json.loads(
            self.session_path.read_text()
        )

        database["website_metadata"].append(data)

        database["session_info"]["tab_count"] += 1

        self.session_path.write_text(
            json.dumps(database, indent=4)
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

    def update_metadata_in_session_json(
        self,
        metadata: dict
    ) -> bool:

        if self.session_path is None:
            raise RuntimeError(
                "No active session JSON has been created."
            )

        database = json.loads(
            self.session_path.read_text()
        )

        for index, existing in enumerate(
            database["website_metadata"]
        ):

            if existing["tab_id"] == metadata["tab_id"]:

                database["website_metadata"][index] = metadata

                self.session_path.write_text(
                    json.dumps(
                        database,
                        indent=4
                    )
                )

                print(
                    "UPDATED TAB IN JSON:",
                    metadata["tab_id"],
                    "TIME:",
                    round(
                        metadata["time_spent"],
                        2
                    )
                )

                return True

        print(
            "COULD NOT FIND TAB TO UPDATE:",
            metadata["tab_id"]
        )

        return False