import random
from datetime import datetime
from dataclasses import dataclass, asdict
from interfaces import IDataManger

@dataclass
class SessionStartInfo:
    id: int
    topic: str
    is_running: bool
    time: float
    start_time:float




class SessionStart:
    def __init__(self):
        self.active_session = False

    def setup_session(self, content:dict):
        
            self.active_session = True
            session_id = self.generate_id()
            topic = content["topic"]
            time = content["minutes"]
            start_time = start_time = int(datetime.now().strftime("%H%M"))
            return SessionStartInfo(session_id,topic,self.active_session,time,start_time)
        #if there is currently a start time running 
        #find it or something...
        #return None

    def generate_id(self):
        return random.randint(0, 100)
    
    def session_start_as_dict(self, content):
        start_session:SessionStartInfo = self.setup_session(content)
        return asdict(start_session)
        
        