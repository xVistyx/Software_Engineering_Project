from datetime import datetime
from pathlib import Path
import json

"""
Need to fix this such that it doesnt use the global db write to JSON but stays local.
It will also need to write the summary and delete the old session json

"""
class UserSessionDataManager:

    def __init__(self):
        self.session_table:str = "sessions"
        self.metadata_table:str = "website_metadata"

        self.session_folder:Path = Path("UserSession/ActiveSessionDB")
        self.session_folder.mkdir(parents=True, exist_ok=True)

        self.session_path: Path | None = None

    
    def create_session_json(self, session_id: int) -> Path:
        self.session_path:Path = (self.session_folder / f"session_{session_id}.json")

        session_data = {
            "session_info": {},
            "website_metadata": []
        }

        self.session_path.write_text(json.dumps(session_data, indent=4))

        return self.session_path

   
    def log_session_start(self, content: dict) -> None:

        

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

    def write_metadata_to_session_json(self, data: dict) -> None:

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
    


    def _make_json_safe(self, value) -> datetime:
        if isinstance(value, datetime):
            return value.isoformat()

        return value

    def update_metadata_in_session_json(self,metadata: dict) -> bool:

        if self.session_path is None:
            raise RuntimeError("No active session JSON has been created.")

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

    def session_end_json(self, session_id: int) -> dict:
        session_path = self.session_folder / f"session_{session_id}.json"

        if not session_path.exists():
            raise FileNotFoundError(
                f"Session JSON not found: {session_path}"
            )

        with session_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def delete_current_session_json(self) -> None:
        if self.session_path is None:
            raise RuntimeError("No active session JSON has been created.")

        if not self.session_path.exists():
            raise FileNotFoundError(
                f"Session JSON not found: {self.session_path}"
            )

        self.session_path.unlink()
        self.session_path = None