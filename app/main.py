from fastapi import FastAPI, APIRouter, Request, WebSocket
from fastapi.responses import ORJSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect

from scalar_fastapi import get_scalar_api_reference

from contextlib import asynccontextmanager

#from rich import print
from rich.traceback import install
from rich.console import Console
from rich.panel import Panel

from enum import Enum

from uuid import UUID

from pathlib import Path

from app.audit.pipeline import audit_pipeline
from app.db.main import init_db, set_admin, migrate, test_db, db_url
from app.api import users, medic_area, auth, cashes, ai_assistant, audit
from app.config import (
    api_name,
    audit_enabled,
    version,
    debug,
    cors_host,
    templates,
    parser_name,
    id_prefix,
    assets_dir,
    media_dir,
)
from app.storage.main import storage
from app.core.auth import time_out, gen_token, decode_token

install(show_locals=True)

console = Console()

main_router = APIRouter(
    prefix=f"/{str(id_prefix)}",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación FastAPI.
    
    Inicializa la base de datos, ejecuta migraciones, configura el usuario administrador
    y crea las tablas de almacenamiento necesarias. En modo debug, también limpia
    recursos al cerrar la aplicación.
    """
    from app.storage.main import storage
    from rich.console import Console
    
    console = Console()
    
    # Inicializar DB
    init_db()
    migrate()
    set_admin()
    
    # Crear todas las tablas necesarias
    required_tables = [
        "ban-token",
        "google-user-data", 
        "recovery-codes",
        "ip-time-out"
    ]
    
    console.print("\n[bold cyan]Inicializando tablas de storage...[/bold cyan]")
    for table_name in required_tables:
        try:
            result = storage.create_table(table_name)
            if result is not None:
                console.print(f"  [green]✓[/green] Tabla '{table_name}' creada")
            else:
                console.print(f"  [yellow]○[/yellow] Tabla '{table_name}' ya existe")
        except Exception as e:
            console.print(f"  [red]✗[/red] Error creando tabla '{table_name}': {e}")
    
    if audit_enabled:
        await audit_pipeline.start()
        
    console.rule("[green]Server Opened[/green]")
    
    if debug:
        console.rule("[bold green]🔍 Documentación Scalar activa[/bold green]")
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
    
    try:
        yield None
    finally:
        if audit_enabled:
            await audit_pipeline.stop()
        console.rule("[red]Server Closed[/red]")
        
        # Cleanup en debug mode...
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
        "name": "LICENSE",
        "url": "https://github.com/Joaquin-Gael/hospital_back/blob/main/LICENSE.txt"
    },
    docs_url=None,
    redoc_url=None,
    debug=debug,
    redirect_slashes=True
)

@main_router.get("/_health_check/")
async def health_check():
    """
    Endpoint de verificación de salud del sistema.
    
    Realiza una prueba de conectividad con la base de datos y mide el tiempo
    de respuesta para determinar el estado de salud del sistema.
    
    Returns:
        ORJSONResponse: Diccionario con tiempo de respuesta y estado de la BD
            - time (float): Tiempo de respuesta en segundos
            - status (bool): True si la BD responde correctamente
            
    Todo:
        Implementar verificaciones más complejas de la base de datos
    """
    # TODO: hacer la comprobacion de la base de datos un una compleja
    result = test_db()
    return ORJSONResponse({"time": result[0],"status": result[1]})

class Layout(Enum):
    MODERN = "modern"
    CLASSIC = "classic"
    DEEP_SPACE = "deepSpace"


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
        """
        Sirve la documentación interactiva Scalar de la API.
        
        Proporciona una interfaz moderna y atractiva para explorar la documentación
        de la API. Solo disponible en modo debug.
        
        Returns:
            HTMLResponse: Página HTML con la interfaz Scalar
            
        Note:
            Esta función solo se registra cuando debug=True
        """
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
            hide_download_button=True,
            layout=Layout.DEEP_SPACE,
            dark_mode=True,
            scalar_favicon_url="/assets/logo-siglas-negro.png"
        )

main_router.include_router(users.router)
main_router.include_router(medic_area.router)
main_router.include_router(auth.router)
main_router.include_router(cashes.router)
if audit_enabled:
    main_router.include_router(audit.router)
main_router.include_router(ai_assistant.router)

app.include_router(main_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #if debug else [cors_host],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.oauth_router)

class SPAStaticFiles(StaticFiles):
    """
    Manejador de archivos estáticos para Single Page Applications.
    
    Extiende StaticFiles para manejar el routing de SPAs, sirviendo archivos
    estáticos cuando existen y redirigiendo a index.html para rutas de SPA.
    Evita conflictos con las rutas de la API.
    
    Attributes:
        api_prefix (str): Prefijo de las rutas de API a evitar
        index_file (str): Archivo index a servir para rutas SPA
    """
    
    def __init__(self, directory: str="templates", html: bool=True, check_dir: bool=True, api_prefix: UUID=id_prefix, index_file: str="index.html"):
        """
        Inicializa el manejador de archivos estáticos SPA.
        
        Args:
            directory (str): Directorio base de archivos estáticos
            html (bool): Si servir archivos HTML
            check_dir (bool): Si verificar que el directorio existe
            api_prefix (UUID): Prefijo de rutas de API a evitar
            index_file (str): Archivo index para rutas SPA
        """
        super().__init__(directory=directory, html=html, check_dir=check_dir)
        self.api_prefix = str(api_prefix)
        self.index_file = index_file

        self.app = super().__call__


    async def __call__(self, scope, receive, send):
        """
        Maneja requests HTTP y WebSocket.
        
        Para HTTP: sirve archivos estáticos si existen, si no redirige a index.html
        para permitir el routing del SPA. Las rutas de API se pasan al handler padre.
        
        Args:
            scope: Scope ASGI de la conexión
            receive: Callable para recibir mensajes ASGI
            send: Callable para enviar mensajes ASGI
        """

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

app.mount("/assets", StaticFiles(directory=assets_dir))
app.mount("/media", StaticFiles(directory=media_dir))

@app.get("/id_prefix_api_secret/", include_in_schema=debug)
async def get_secret():
    """
    Obtiene el prefijo secreto de la API.
    
    Proporciona el ID del prefijo utilizado en las rutas de la API para
    configuración de clientes y herramientas de desarrollo.
    
    Returns:
        dict: Diccionario con el prefijo secreto de la API
            - id_prefix_api_secret (str): UUID del prefijo de la API
            
    Note:
        Solo incluido en el schema cuando debug=True
    """
    return {"id_prefix_api_secret": str(id_prefix)}

@app.websocket("/{secret}/ws")
async def websocket_endpoint(websocket: WebSocket, secret: str):
    """
    Endpoint WebSocket para comunicación en tiempo real.
    
    Establece una conexión WebSocket que acepta mensajes JSON y los devuelve
    como eco. Maneja desconexiones y errores de manera robusta.
    
    Args:
        websocket (WebSocket): Instancia de la conexión WebSocket
        secret (str): Parámetro de ruta (no validado actualmente)
        
    Raises:
        WebSocketDisconnect: Cuando el cliente se desconecta
        Exception: Para cualquier otro error en la comunicación
        
    Note:
        Actualmente implementa funcionalidad de eco básica.
        El parámetro 'secret' no se valida.
    """
    await websocket.accept()
    # Enviar mensaje de bienvenida
    await websocket.send_json({"message": "Hello WebSocket"})
    
    try:
        while True:
            # Recibir y hacer eco del mensaje
            data = await websocket.receive_json()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        console.print("Cliente desconectado")
    except Exception as e:
        console.print_exception(show_locals=True)
        console.print(f"Error en WebSocket: {str(e)}")

@app.get("/login-admin")
@time_out(120)
async def login_admin(request: Request):
    return templates.TemplateResponse(parser_name(["admin", "login"], "login"), {"request": request})

@app.get("/admin")
@time_out(120)
async def admin(request: Request):
    session = request.cookies.get("session")
    try:
        decode_token(session)
        return templates.TemplateResponse(parser_name(["admin", "panel"], "index"), {"request": request})
    except:
        return templates.TemplateResponse(parser_name(["admin", "login"], "login"), {"request": request})

#app.mount("/", SPAStaticFiles(), name="spa")