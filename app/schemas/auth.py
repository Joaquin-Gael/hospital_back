from pydantic import BaseModel

from app.schemas.medica_area import DoctorResponse

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