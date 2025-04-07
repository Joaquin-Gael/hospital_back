from fastapi import FastAPI

from contextlib import asynccontextmanager

from rich import print

from app.db.main import init_db
from app.api import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")
    print("Server opened")
    yield None
    print("Server closed")

app = FastAPI(lifespan=lifespan)