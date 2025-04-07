from fastapi import APIRouter, Request, Depends
from fastapi.responses import ORJSONResponse

from sqlalchemy import select

from typing import List

from app.schemas.users import UserRead
from app.models.users import User
from app.db.main import SessionDep

router = APIRouter(
    tags=["users"],
    responses={404: {"description": "Not found"}},
    prefix="/users",
    default_response_class=ORJSONResponse,
)

@router.get("/", response_model=List[UserRead])
async def get_users(request: Request, session: SessionDep):
    statement = select(User)
    result = session.execute(statement)
    users = []
    for user in result.scalars().all():
        users.append(
            UserRead(
                id=user.id,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                date_joined=user.date_joined,
            )
        )

    return ORJSONResponse(users)

@router.get("/add/")
async def add_user(request: Request, session: SessionDep):
    pass