from pydantic import BaseModel

from app.schemas.users import UserRead

class TokenUserResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: UserRead
