import jwt
from jwt import PyJWTError

from datetime import datetime, timedelta

from fastapi import Header, HTTPException, status, Request

from sqlmodel import select

from typing import Optional

from app.config import token_key, api_name, version
from app.models.users import User
from app.db.main import Session, engine

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

    async def __call__(self, request: Request, authorization: Optional[str] = Header(None)) -> User | None:
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

        token = authorization.split(" ")[1]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            statement = select(User).where(User.id == user_id)
            with Session(engine) as session:
                result = session.execute(statement)
                user = result.scalars().first()
            request.state.user = user
            return user
        except Exception as e:
            print(e)
            raise HTTPException(status_code=401, detail="Invalid or expired token")