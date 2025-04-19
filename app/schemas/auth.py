from pydantic import BaseModel

from app.schemas.users import UserRead
from app.schemas.medica_area import DoctorResponse

class TokenUserResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: UserRead


class TokenDoctorsResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    doc: DoctorResponse