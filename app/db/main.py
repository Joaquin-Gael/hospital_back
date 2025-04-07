from sqlmodel import create_engine, Session, SQLModel
from typing import Annotated
from fastapi import Depends

DB_URL = f"sqlite:///db.sqlite"

engine = create_engine(DB_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]