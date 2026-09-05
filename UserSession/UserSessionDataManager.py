from interfaces import IDataManger

class UserSessionDataManager():
    def log_session_start(self, content:dict, data_manger:IDataManger):
        
        data_manger.write_to_db(content)