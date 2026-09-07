from interfaces import IDataManger

class UserSessionDataManager():
    def __int__(self):
        self.global_data_manager = None

    def set_global_data_manager(self, data_manager:IDataManger):
        self.global_data_manager = data_manager


    def log_session_start(self, content:dict):  
        self.global_data_manager.write_to_db(content)

    #need to add funtionality to add the ability to check for active session and return them