import jwt
from jwt import PyJWTError

from datetime import datetime, timedelta

from pydantic import BaseModel

from fastapi import Header, HTTPException, status, Request, Cookie, Query

from functools import singledispatch

from sqlmodel import select

from typing import Optional, Any, Type, TypeVar

from cryptography.fernet import Fernet

from json import loads, dumps, JSONDecodeError

from uuid import UUID

from rich.console import Console

import logging

import sys

from app.config import token_key, api_name, version
from app.models.users import User
from app.models.medic_area import Doctors
from app.db.main import Session, engine

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
handler.setFormatter(formatter)

logger.addHandler(handler)

encoder_key = Fernet.generate_key()

encoder_f = Fernet(encoder_key)

console = Console()

@singledispatch
def encode(data: object) -> bytes:
    try:
        text = dumps(data, default=lambda o: o.__dict__, sort_keys=True)
    except TypeError:
        text = str(data)
    return encoder_f.encrypt(text.encode("utf-8"))

@encode.register
def _(data: str) -> bytes:
    # Texto plano → bytes
    return encoder_f.encrypt(data.encode("utf-8"))

@encode.register
def _(data: UUID) -> bytes:
    # UUID → cadena → bytes
    return encoder_f.encrypt(str(data).encode("utf-8"))

@encode.register
def _(data: BaseModel) -> bytes:
    # Pydantic v2: modelo → JSON string
    json_str = data.model_dump_json()
    return encoder_f.encrypt(json_str.encode("utf-8"))

@encode.register
def _(data: dict) -> bytes:
    # JSON: diccionario → bytes
    text = dumps(data, sort_keys=True).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: list) -> bytes:
    # JSON: lista → bytes
    text = dumps(data).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: tuple) -> bytes:
    # JSON trata tuplas como arrays; las convertimos a lista
    text = dumps(list(data)).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: int) -> bytes:
    # JSON: entero → bytes
    text = dumps(data).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: float) -> bytes:
    # JSON: flotante → bytes
    text = dumps(data).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: bool) -> bytes:
    # JSON: booleano → bytes
    text = dumps(data).encode("utf-8")
    return encoder_f.encrypt(text)

@encode.register
def _(data: type(None)) -> bytes:
    # JSON: None → "null"
    text = dumps(data).encode("utf-8")
    return encoder_f.encrypt(text)




T = TypeVar("T")

def decode(data: bytes, dtype: Type[T] | None = None) -> T | Any:
    try:
        plaintext: bytes = encoder_f.decrypt(data)
    except Exception as e:
        console.print_exception(show_locals=True)
        raise ValueError("Token inválido o expirado") from e


    text = plaintext.decode("utf-8")

    try:
        obj = loads(text)
    except JSONDecodeError:
        obj = text

    if dtype is None:
        return obj

    if isinstance(dtype, type) and issubclass(dtype, BaseModel):
        return dtype.model_validate(obj)

    if dtype in (dict, list, tuple, str, int, float, bool):
        return dtype(obj)

    return dtype(obj)

def gen_token(payload: dict, refresh: bool = False):
    payload.setdefault("iat", datetime.now())
    payload.setdefault("iss", f"{api_name}/{version}")
    if refresh:
        payload.setdefault("exp", int((datetime.now() + timedelta(minutes=30)).timestamp()))
        payload.setdefault("type", "refresh_token")
    else:
        payload.setdefault("exp", int((datetime.now() + timedelta(minutes=15)).timestamp()))
    return jwt.encode(payload, token_key, algorithm="HS256")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, key=token_key, algorithms=["HS256"], leeway=20)
        return payload
    except PyJWTError as e:
        print(e)
        raise ValueError("Value Not Found") from e

class JWTBearer:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request, authorization: Optional[str] = Header(None), session: Optional[str] = Cookie(None)) -> User | Doctors | None: # TODO: , session: str = Cookie(...)
        if authorization is None or not authorization.startswith("Bearer "):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No credentials provided or invalid format"
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No credentials provided or invalid format"
            )

        if session is None:
            logger.debug(f"Session Token: {session}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No session provided or invalid format"
            )

        token = authorization.split(" ")[1]
        cookie_token = session
        try:
            payload = decode_token(token)
            cookie_payload = decode_token(cookie_token)
            user_id = payload.get("sub")
            cookie_user_id = cookie_payload.get("sub")
            if (user_id is None or cookie_user_id is None) or (user_id != cookie_user_id):
            #if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            if "doc" in payload.get("scopes"):
                statement = select(Doctors).where(Doctors.id == user_id)
            else:
                statement = select(User).where(User.id == user_id)

            with Session(engine) as session:
                result = session.execute(statement)
                user = result.scalars().first()

            request.state.user = user

            return user

        except Exception as e:
            print(e)
            raise HTTPException(status_code=401, detail="Invalid or expired token")

class JWTWebSocket:
    async def __call__(self, token:str = Query(...)):
        if not token or token.startswith("Bearer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No credentials provided or invalid format"
            )

        token = token.split("_")[1]

        payload = decode_token(token)
        user_id = payload.get("sub", None)

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        if "doc" in payload.get("scopes"):
            statement = select(Doctors).where(Doctors.id == user_id)
        else:
            statement = select(User).where(User.id == user_id)

        with Session(engine) as session:
            result = session.execute(statement)
            user = result.scalars().first()

        return user