import json
"""
This is a baby version just testing with JSON and experimenting with the data Flow 
"""

class DataManager:
    def __init__(self):
        self.file_path = "DataBase/Db.json"

    def write_to_db(self, input: dict) -> None:
        with open(self.file_path, "w") as file:
            json.dump(input, file, indent=4)

    def read_from_db(self) -> dict:
        try:
            with open(self.file_path, "r") as file:
                return json.load(file)

        except FileNotFoundError:
            return {}