from interfaces import ISettings
import json
from os.path import isfile

settingfile = "settings.json"
blocklistfile = "blocklist.json"


class Settings:

    def __init__(self):
        self.settings = {
            "defaultMinutes" : 45,
            "breakReminders" : True,
            "sounds" : True,
            "strictMode" : False
        }

        self.blocklist = {
            "sites" : []
        }
        self.load_blocklist()
        self.load_settings()
    
    def settings_manager(self, action:str, content:dict):
        if action == "get_settings":
            return self.get_settings()
        elif action == "update_settings":
            return self.update_settings(content)
        elif action == "get_blocklist":
            return self.get_blocklist()
        elif action == "update_blocklist":
            return self.update_blocklist(content)
        else:
            return {"action":action, "content": {}}
    
    def get_settings(self):
        return {"action":"get_settings", "content":self.settings}
    def update_settings(self, content:dict):
        for ele in content:
            if ele in self.settings:
                self.settings[ele] = content[ele]
        #thing to update database, use function
        self.save_settings()
        return {"action":"update_settings", "content":self.settings}
    def get_blocklist(self):
        return {"action":"get_blocklist", "content": self.blocklist}
    def update_blocklist(self, content:dict):
        if "sites" in content:
            self.blocklist["sites"] = content["sites"]
        #update the blocklist in database, use function
        self.save_blocklist()
        return {"action":"update_blocklist", "content":self.blocklist}

    def load_settings(self):
        if isfile(settingfile):
            with open(settingfile, "r") as fp:
                self.settings = json.load(fp)
    def load_blocklist(self):
        if isfile(blocklistfile):
            with open(blocklistfile, "r") as fp:
                self.blocklist = json.load(fp)
    def save_settings(self):
        with open(settingfile, "w") as fp:
            json.dump(self.settings, fp)
    def save_blocklist(self):
        with open(blocklistfile, "w") as fp:
            json.dump(self.blocklist, fp)
    