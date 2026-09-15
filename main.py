import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from System.System import System, AuthorizationError
from System.BackendRequests import SessionData, BackendResponse


def create_app(system=None):
    system = system or System()

    @asynccontextmanager
    async def lifespan(app):
        async def checkpoint_loop():
            while True:
                await asyncio.sleep(5)
                try:
                    await asyncio.to_thread(system.checkpoint)
                except Exception:
                    logging.exception('Could not persist a checkpoint; will retry')
        task = asyncio.create_task(checkpoint_loop())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            system.checkpoint()

    app = FastAPI(lifespan=lifespan)
    app.state.system = system
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173'],
                       allow_methods=['POST'], allow_headers=['Content-Type', 'Authorization'])
    bearer = HTTPBearer(auto_error=False)

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        try:
            identity = system.authenticate(credentials.credentials if credentials else None)
        except (sqlite3.Error, OSError) as error:
            raise HTTPException(503, 'Storage is unavailable. Please retry.') from error
        if identity is None:
            raise HTTPException(401, 'Connect your profile with its access key.', headers={'WWW-Authenticate': 'Bearer'})
        return identity

    @app.post('/backend', response_model=BackendResponse)
    def receive_message(data: SessionData, identity=Depends(principal)):
        try:
            return system.handle_request(data.model_dump(), identity)
        except AuthorizationError as error:
            raise HTTPException(403, str(error)) from error
        except ValueError as error:
            raise HTTPException(404 if str(error) == 'Session not found' else 400, str(error)) from error
        except (sqlite3.Error, OSError) as error:
            logging.exception('Storage operation failed')
            raise HTTPException(503, 'Storage is unavailable. Retained session data will be retried.') from error
    return app


app = create_app()
