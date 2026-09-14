import json
from pathlib import Path


class DataManager:

    def __init__(self):
        self.session_db_file = Path("DataBase/Db.json")
        self.metadata_db_file = Path("DataBase/MetaDataDatabase.json")

        self.session_db_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize session database if missing OR empty
        if (
            not self.session_db_file.exists()
            or not self.session_db_file.read_text().strip()
        ):
            self.session_db_file.write_text(
                json.dumps({
                    "sessions": []
                }, indent=4)
            )

        # Initialize metadata database if missing OR empty
        if (
            not self.metadata_db_file.exists()
            or not self.metadata_db_file.read_text().strip()
        ):
            self.metadata_db_file.write_text(
                json.dumps({
                    "website_metadata": []
                }, indent=4)
            )

    def get_db_file(self, table: str) -> Path:

        if table == "website_metadata":
            return self.metadata_db_file

        return self.session_db_file

    def write_to_db(self, table: str, data: dict):

        db_file = self.get_db_file(table)

        database = json.loads(
            db_file.read_text()
        )

        if table not in database:
            database[table] = []

        database[table].append(data)

        db_file.write_text(
            json.dumps(database, indent=4)
        )

        print("WRITE SUCCESSFUL:", db_file.resolve())

    def read_from_db(self, table: str):

        db_file = self.get_db_file(table)

        database = json.loads(
            db_file.read_text()
        )

        return database.get(table, [])