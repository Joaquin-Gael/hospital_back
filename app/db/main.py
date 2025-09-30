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
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

metadata = SQLModel.metadata