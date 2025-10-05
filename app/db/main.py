from sqlmodel import create_engine, Session, SQLModel, select

from sqlalchemy.exc import IntegrityError

from typing import Annotated

from fastapi import Depends

from rich import print
from rich.console import Console

from subprocess import run

import time

from typing import List, Tuple

from app.config import debug, admin_user, User, db_url


engine = create_engine(db_url, echo=False, future=True, pool_pre_ping=True)

console = Console()

def init_db():
    """
    Inicializa el esquema de la base de datos.
    
    Crea todas las tablas definidas en los modelos SQLModel si no existen.
    Esta operación es idempotente - no recreará tablas existentes.
    
    Note:
        - Usa SQLModel.metadata.create_all() para crear tablas
        - No elimina datos existentes
        - Debe ejecutarse antes de usar la aplicación
    """
    print("Initializing database")
    SQLModel.metadata.create_all(engine)
    print("Database initialized")

def migrate():
    """
    Ejecuta migraciones pendientes de la base de datos usando Alembic.
    
    Aplica todas las migraciones pendientes hasta la revisión 'head',
    actualizando el esquema de la base de datos según los cambios
    en los modelos.
    
    Note:
        - Ejecuta 'alembic upgrade head'
        - Muestra output detallado en modo debug
        - Captura tanto stdout como stderr para logging
    """
    out = run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    print("Database migrated:\n")
    if out.stderr:
        print(out.stderr) if debug else None
    else:
        print(out.stdout) if debug else None

def set_admin():
    """
    Crea el usuario administrador inicial del sistema.
    
    Verifica si ya existe un administrador con el email configurado.
    Si no existe, crea el usuario admin usando los datos de configuración.
    
    Raises:
        IntegrityError: Si hay conflictos de integridad (usuario ya existe)
        Exception: Para otros errores durante la creación
        
    Note:
        - Solo crea el admin si no existe previamente
        - Usa admin_user de la configuración del sistema
        - Operación idempotente - segura para ejecutar múltiples veces
    """
    try:
        print("Setting admin")
        with Session(engine) as session:
            admin: User = session.exec(
                select(User)
                    .where(User.email == admin_user.email)
            ).first()

            if admin:
                return

            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
        print("Admin created")
    except IntegrityError:
        console.print_exception(show_locals=True) if debug else None
        print("Admin already created")

    except Exception(BaseException):
        console.print_exception(show_locals=True) if debug else None
        print("Admin not created")


def test_db() -> Tuple[float, bool]:
    """
    Prueba la conectividad y rendimiento de la base de datos.
    
    Ejecuta una consulta simple para verificar que la base de datos
    está funcionando correctamente y mide el tiempo de respuesta.
    
    Returns:
        Tuple[float, bool]: Tupla con (tiempo_respuesta, éxito)
            - tiempo_respuesta (float): Tiempo en segundos que tardó la consulta
            - éxito (bool): True si la consulta fue exitosa, False si falló
            
    Note:
        - Usado por el endpoint /_health_check/ para monitoreo
        - Ejecuta SELECT sobre la tabla User
        - Incluye manejo de excepciones para errors de BD
    """
    start = time.time()
    try:
        with Session(engine) as session:
            statement = select(User)
        result: List["User"] = session.exec(statement).all()
        if result is None:
            end = time.time()
            return (end - start), False

        end = time.time()

        return (end - start), True

    except Exception:
        end = time.time()
        console.print_exception(show_locals=True) if debug else None
        return (end - start), False


def get_session():
    """
    Generador de sesiones de base de datos para dependency injection.
    
    Crea una nueva sesión SQLModel para cada request, garantizando
    el cierre automático de la conexión al finalizar.
    
    Yields:
        Session: Sesión de base de datos para operaciones ORM
        
    Note:
        - Patrón context manager con yield
        - Usado como FastAPI Dependency
        - Garantiza cierre automático de conexiones
        - Una sesión por request para thread safety
    """
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

metadata = SQLModel.metadata