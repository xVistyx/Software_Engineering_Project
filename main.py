import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from System.System import System
from System.BackendRequests import SessionData, BackendResponse


system = System()


@asynccontextmanager
async def lifespan(app):
    async def checkpoint_loop():
        while True:
            await asyncio.sleep(5)
            try:
                await asyncio.to_thread(system.tracker.checkpoint)
            except Exception:
                logging.exception('Could not persist the session checkpoint; will retry')

    task = asyncio.create_task(checkpoint_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    system.tracker.checkpoint()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173'],
                   allow_methods=['POST'], allow_headers=['Content-Type'])


@app.post('/backend', response_model=BackendResponse)
def receive_message(data: SessionData):
    try:
        return system.send_requests_to_frontend(system.buildResponse(data.model_dump()))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
