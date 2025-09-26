from pydantic import BaseModel

from app.schemas.medica_area import DoctorResponse

from datetime import datetime

from uuid import UUID

from sqlmodel import SQLModel, Field

from uuid import uuid4

class TokenUserResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenDoctorsResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    doc: DoctorResponse

class OauthCodeInput(BaseModel):
    code: str
