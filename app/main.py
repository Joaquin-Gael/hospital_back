from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from rich import print
from rich.traceback import install

from app.db.main import init_db, set_admin, migrate
from app.api import users, medic_area, auth
from app.config import api_name, version

install(show_locals=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate()
    set_admin()
    print("Server opened")
    yield None
    print("Server closed")

app = FastAPI(
    lifespan=lifespan,
    title=api_name,
    description="Esta API permite gestionar usuarios, pacientes y médicos.",
    version=version,
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
app.include_router(medic_area.router)
app.include_router(auth.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)