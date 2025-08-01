from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import ORJSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from scalar_fastapi import get_scalar_api_reference

from contextlib import asynccontextmanager

#from rich import print
from rich.traceback import install
from rich.console import Console
from rich.panel import Panel

from enum import Enum

from uuid import uuid4, UUID

from pathlib import Path

from app.db.main import init_db, set_admin, migrate, test_db, db_url
from app.api import users, medic_area, auth
from app.config import api_name, version, debug, cors_host, templates, parser_name
from app.storage.main import storage

install(show_locals=True)

console = Console()

id_prefix: UUID = uuid4()

main_router = APIRouter(
    prefix=f"/{str(id_prefix)}",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate()
    set_admin()
    storage.create_table("ban-token")
    storage.create_table("google-user-data")
    console.rule("[green]Server Opened[/green]")
    if debug:
        # Línea destacada con título
        console.rule("[bold green]🔍 Documentación Scalar activa[/bold green]")

        # Panel con el mensaje y detalles
        mensaje = (
            "[bold cyan]La documentación de tu API está disponible en:[/bold cyan]\n"
            f"  [bold magenta]http://localhost:8000/{id_prefix}/scalar[/bold magenta]\n\n"
            "[dim]Permanecerá accesible mientras debug esté activado.[/dim]"
        )
        console.print(
            Panel.fit(
                mensaje,
                title="[bold yellow]📚 Scalar Docs[/bold yellow]",
                border_style="bright_blue",
                padding=(1, 2),
            )
        )
    yield None
    console.rule("[red]Server Closed[/red]")
    if debug:
        try:
            import os
            from pathlib import Path
            import time

            db_name = db_url.split("/")[-1]
            db_driver = db_url.split(":")[0]

            if db_driver == "sqlite":
                db_path = Path(db_name).resolve()

                for _ in range(5):
                    try:
                        db_path.unlink()
                        os.remove(db_path)
                        break
                    except PermissionError:
                        console.print_exception()
                        time.sleep(1)
            else:
                pass

        except OSError:
            console.print_exception(show_locals=True)

app = FastAPI(
    lifespan=lifespan,
    title=api_name,
    description="Esta API permite gestionar usuarios, pacientes y médicos.",
    version=version,
    contact={
        "name": "JoaDev",
        "email": "tuemail@example.com",
        "url": "https://tuweb.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url=None,
    redoc_url=None,
    debug=debug,
    redirect_slashes=True
)

@main_router.get("/_health_check/")
async def health_check():
    # TODO: hacer la comprobacion de la base de datos un una compleja
    result = test_db()
    return ORJSONResponse({"time": result[0],"status": result[1]})

class Layout(Enum):
    MODERN = "modern"
    CLASSIC = "classic"


class SearchHotKey(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"

if debug:
    @main_router.get("/scalar", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
            hide_download_button=True,
            layout=Layout.MODERN,
            dark_mode=True,
            scalar_favicon_url="/assets/logo-siglas-negro.png"
        )

main_router.include_router(users.router)
main_router.include_router(medic_area.router)
main_router.include_router(auth.router)

app.include_router(main_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"] if debug else [cors_host],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.oauth_router)

class SPAStaticFiles(StaticFiles):
    def __init__(self, directory: str="dist/hospital-sdlg/browser", html: bool=True, check_dir: bool=True, api_prefix: UUID=id_prefix, index_file: str="index.html"):
        super().__init__(directory=directory, html=html, check_dir=check_dir)
        self.api_prefix = str(api_prefix)
        self.index_file = index_file

        self.app = super().__call__


    async def __call__(self, scope, receive, send):

        if scope["type"] == "websocket":
            return await self.app(scope, receive, send)

        assert scope["type"] == "http"

        request = Request(scope, receive)

        path = request.url.path.lstrip("/")

        if request.url.path.startswith(self.api_prefix):
            await self.app(scope, receive, send)
            return

        full_path = (Path(self.directory) / path).resolve()
        if full_path.exists():
            await self.app(scope, receive, send)
            return

        index_path = Path(self.directory) /self.index_file
        response = FileResponse(index_path)
        await response(scope, receive, send)

@app.get("/id_prefix_api_secret/", include_in_schema=debug)
async def get_secret():
    return {"id_prefix_api_secret": str(id_prefix)}

@app.get("/test/oauth/")
async def oauth_index(request: Request):
    return templates.TemplateResponse(request, name=parser_name(folders=["test", "oauth"], name="index"))

@app.get("/test/oauth/login")
async def oauth_index(request: Request):
    return templates.TemplateResponse(request, name=parser_name(folders=["test", "oauth"], name="login"))

@app.get("/user_panel")
async def user_panel(request:Request):
    return templates.TemplateResponse(request, name=parser_name(folders=["test", "oauth"], name="panel"))

#app.mount("/", SPAStaticFiles(), name="spa")