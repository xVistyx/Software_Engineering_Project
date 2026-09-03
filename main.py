from System.System import System
from System.BackendRequests import SessionData
from fastapi import FastAPI
from interfaces import ISystem


app = FastAPI()
system = System()


@app.post("/backend")
def receive_message(data: SessionData):

    # Convert received frontend JSON into dictionary
    message = data.model_dump()

    # FRONTEND -> BACKEND
    system.fetch_requests_from_frontend(message)

    # Backend creates whatever response it wants
    response = {
        "action": data.action,
        "content": {
            "BackendContent":data.content,
            "status": "received"
        }
    }
    # BACKEND -> FRONTEND
    return system.send_requests_to_frontend(response)