from sqlmodel import create_engine, Session, SQLModel, select

from typing import Annotated

from fastapi import Depends

from rich import print
from rich.console import Console

from subprocess import run

import time

from typing import List, Tuple

from app.config import debug, admin_user, User

#from mako.testing.helpers import result_lines #TODO: testear

DB_URL_TEST = f"postgresql+psycopg2://postgres:4321@localhost:5433/dev"

engine = create_engine(DB_URL_TEST, echo=debug)

console = Console()

def init_db():
    print("Initializing database")
    SQLModel.metadata.create_all(engine)
    print("Database initialized")

def migrate():
    out = run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    print("Database migrated:\n")
    if out.stderr:
        print(out.stderr) if debug else None
    else:
        print(out.stdout) if debug else None

def set_admin():
    try:
        print("Setting admin")
        with Session(engine) as session:
            admin: User = session.execute(
                select(User)
                    .where(User.email == admin_user.email)
            ).scalars().first()

            if admin:
                return

            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
        print("Admin created")
    except Exception:
        console.print_exception(show_locals=True) if debug else None
        print("Admin already created")


def test_db() -> Tuple[float, bool]:
    start = time.time()
    try:
        with Session(engine) as session:
            statement = select(User)
        result: List["User"] = session.execute(statement).scalars().all()
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
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

metadata = SQLModel.metadata