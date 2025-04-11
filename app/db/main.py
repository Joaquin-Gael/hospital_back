from sqlmodel import create_engine, Session, SQLModel, select

from typing import Annotated

from fastapi import Depends

from rich import print

from subprocess import run

from app.config import debug, admin_user, User

DB_URL = f"sqlite:///db.sqlite"

engine = create_engine(DB_URL, echo=debug)

def init_db():
    print("Initializing database")
    SQLModel.metadata.create_all(engine)
    print("Database initialized")

def migrate():
    out = run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    print("Database migrated:\n")
    if out.stderr:
        print(out.stderr)
    else:
        print(out.stdout)

def set_admin():
    try:
        print("Setting admin")
        with Session(engine) as session:
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
        print("Admin created")
    except Exception as e:
        print(e)
        print("Admin already created")


def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]