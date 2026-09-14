from System.System import System
from System.BackendRequests import SessionData
from fastapi import FastAPI



app = FastAPI()
system = System()


@app.post("/backend")
def receive_message(data: SessionData):

    # Convert received frontend JSON into dictionary
    message = data.model_dump()

    # FRONTEND -> BACKEND
    # Backend creates whatever response it wants
    response:dict = system.buildResponse(message)
    # this response is a demo it will need to be made nicer

   
    # BACKEND -> FRONTEND
    return system.send_requests_to_frontend(response)