
"""
Here i need to get access to the front end via the fast API connection
"""

from pydantic import BaseModel
class SessionData(BaseModel):
    action: str
    content: dict

    

class BackendRequests:
    
    def handle_requests(self, message:dict): #information from frontend getter frontend -> backend

        return message
     
    def build_responses(self,message: dict) -> SessionData: #information being sent to frontend setter backend -> frontend
            """
            the message should be formatted in such a way that i can build session data from it and pass it to the front end
            it must contain 
            - an action (which frontend will use to )
            the content which is the message information 
            """

            return SessionData(
            action=message["action"],
            content=message["content"]
        )


    
        