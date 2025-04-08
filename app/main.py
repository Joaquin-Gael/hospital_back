from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from rich import print
from rich.traceback import install

from subprocess import run

from app.db.main import init_db, Session, engine
from app.api import users
from app.config import admin_user

install(show_locals=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database created")
    out = run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    print("Database migrated:\n")
    if out.stderr:
        print(out.stderr)
    else:
        print(out.stdout)
    with Session(engine) as session:
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
    print("Server opened")
    yield None
    print("Server closed")

app = FastAPI(
    lifespan=lifespan,
    title="Hospital API",
    description="Esta API permite gestionar usuarios, pacientes y médicos.",
    version="1.0.0",
    contact={
        "name": "Tu Nombre o Equipo",
        "email": "tuemail@example.com",
        "url": "https://tuweb.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

@app.get("/_health_check/")
async def health_check():
    # TODO: hacer la comprobacion de la base de datos un una peticion simple y otra compleja
    return ORJSONResponse({"status": "ok"})

app.include_router(users.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)