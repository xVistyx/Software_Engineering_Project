from System.System import System
from System.BackendRequests import SessionData

from fastapi import FastAPI, Header, HTTPException


app = FastAPI()
system = System()

@app.post("/register")
def register_user():
    return system.system_manager.user_manager.register_user()
@app.post("/backend")
def receive_message(data: SessionData,authorization: str = Header(None)):

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization token"
        )

    # Expected format:
    # Authorization: Bearer <token>

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format"
        )

    token = authorization.removeprefix("Bearer ").strip()

    message = data.model_dump()

    try:
        response = system.buildResponse(message,token)

    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error)
        )

    return system.send_requests_to_frontend(response)