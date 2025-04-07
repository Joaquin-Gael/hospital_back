from fastapi import FastAPI

from contextlib import asynccontextmanager

from fastapi.responses import ORJSONResponse
from rich import print

from app.db.main import init_db
from app.api import users

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    print("Server opened")
    yield None
    print("Server closed")

app = FastAPI(lifespan=lifespan)

@app.get("/_health_check/")
async def health_check():
    # TODO: hacer la comprobacion de la base de datos un una peticion simple y otra compleja
    return ORJSONResponse({"status": "ok"})

app.include_router(users.router)