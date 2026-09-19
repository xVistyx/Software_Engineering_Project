import json
from pathlib import Path
from DataBase.IDataBaseManager import IDataBaseManager
from DataBase.SessionRepository import SessionRepository
from DataBase.SummaryAdapter import summary_record


class DataBaseManager(IDataBaseManager):
    """SQL implementation of the team's System-facing storage interface.

    This component only stores supplied data and returns saved records. It never
    calls System, session tracking, temporary-file handling, frontend, or AI code.
    """

    def __init__(self, repository=None):
        self.repository = repository if repository is not None else SessionRepository()

    def get_users(self):
        return self.repository.users()
    def create_user(self, user_id, token):
        return self.repository.create_user(user_id, token)

    def authenticate(self, token):
        return self.repository.authenticate(token) if token else None

    def get_preferences(self, user_id, defaults):
        return self.repository.preferences(user_id, defaults)

    def save_preferences(self, user_id, data):
        self.repository.save_preferences(user_id, data)

    def save_session(self, user_id, data):
        """This is the entry point i gotta use. """
        session, summary = summary_record(user_id, data)
        self.repository.save_session(user_id, session, summary)

    def get_history(self, user_id):
        return self.repository.list(user_id)

    def get_session_details(self, user_id, session_id):
        return self.repository.get(user_id, session_id)

    def get_legacy_sources(self, user_id):
        return self.repository.legacy_sources(user_id)

    def get_ai_session(self, user_id, session_id):
        return self.repository.ai_input(user_id, session_id)

    def save_session_analysis(self, user_id, session_id, analysis):
        return self.repository.save_analysis(user_id, session_id, analysis)


class DataManager:
    """Legacy JSON prototype; retained for old imports, unused by the running app."""

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


"""
old
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

"""

