from fastapi import APIRouter, Request, Depends, HTTPException, Header, status
from fastapi.responses import ORJSONResponse

from rich.console import Console

from typing import Optional, Dict, List

from sqlmodel import select

from datetime import datetime

from app.models import Doctors, User
from app.db.main import SessionDep
from app.core.auth import gen_token, JWTBearer, decode
from app.core.interfaces.oauth import OauthRepository
from app.core.interfaces.users import UserRepository
from app.core.interfaces.emails import EmailService
from app.schemas.users import UserAuth
from app.schemas.auth import TokenUserResponse, TokenDoctorsResponse
from app.schemas.medica_area import DoctorAuth, DoctorResponse
from app.storage import storage

console = Console()

auth = JWTBearer()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

oauth_router = APIRouter(
    prefix="/oauth",
    tags=["oauth"]
)

@router.get("/scopes", response_model=Dict[str, List[str]])
async def get_scopes(request: Request, _=Depends(auth)):
    scopes = request.state.scopes
    return ORJSONResponse({
        "scopes":scopes,
    })

@router.post("/decode/")
async def decode_hex(code: str):
    bytes_code = bytes.fromhex(code)
    return decode(bytes_code, dict)

@router.post("/doc/login", response_model=TokenDoctorsResponse)
async def doc_login(session: SessionDep, credentials: DoctorAuth):
    statement = select(Doctors).where(Doctors.email == credentials.email)
    result = session.exec(statement)
    doc: Doctors = result.first()
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid credentials")

    if not doc.check_password(credentials.password):
        raise HTTPException(status_code=404, detail="Invalid credentials")

    doc_data = {
        "sub":str(doc.id),
        "scopes":["doc"]
    }

    if doc.is_active:
        doc_data["scopes"].append("active")

    token = gen_token(doc_data)
    refresh_token = gen_token(doc_data)

    return ORJSONResponse(
        TokenDoctorsResponse(
            access_token=token,
            token_type="Bearer",
            doc=DoctorResponse(
                id=doc.id,
                username=doc.name,
                last_name=doc.last_name,
                first_name=doc.first_name,
                dni=doc.dni,
                telephone=doc.telephone,
                email=doc.email,
                speciality_id=doc.speciality_id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
            ),
            refresh_token=refresh_token
        ).model_dump()
    )

@router.post("/login", response_model=TokenUserResponse)
async def login(session: SessionDep, credentials: UserAuth):
    statement = select(User).where(User.email == credentials.email)
    result = session.exec(statement)
    user: User = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid credentials payload")

    if not user.check_password(credentials.password):
        raise HTTPException(status_code=400, detail="Invalid credentials payload")

    user_data = {
        "sub":str(user.id),
        "scopes":[]
    }

    if user.is_admin:
        user_data["scopes"].append("admin")

    if user.is_superuser:
        user_data["scopes"].append("superuser")
    else:
        user_data["scopes"].append("user")

    if user.is_active:
        user_data["scopes"].append("active")

    token = gen_token(user_data)
    refresh_token = gen_token(user_data, refresh=True)

    user.last_login = datetime.now()

    session.add(user)
    session.commit()
    session.refresh(user)

    return ORJSONResponse(
        TokenUserResponse(
            access_token=token,
            token_type="Bearer",
            refresh_token=refresh_token,
        ).model_dump()
    )

@oauth_router.get("/{service}/")
async def oauth_login(service: str):
    try:
        match service:
            case "google":
                return OauthRepository.google_oauth()
            case _:
                raise HTTPException(status_code=501, detail="Not Implemented")
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@oauth_router.get("/webhook/google_callback")
async def google_callback(request: Request):
    try:
        params: dict = dict(request.query_params)
        data, exist, response = OauthRepository.google_callback(params.get("code"))
        if not exist:
            EmailService.send_welcome_email(
                email=data.get("email"),
                first_name=data.get("given_name"),
                last_name=data.get("family_name")
            )
            EmailService.send_google_account_linked_password(email=data.get("email"), first_name=data.get("given_name"),
                                                             last_name=data.get("family_name"),
                                                             raw_password=data.get("id"))

        return response
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/refresh", response_model=TokenUserResponse, name="refresh_token")
async def refresh(user: User = Depends(auth)):

    if isinstance(user, Doctors):
        doc_data = {
            "sub":str(user.id),
            "scopes":["doc"]
        }

        if user.is_active:
            doc_data["scopes"].append("active")


        token = gen_token(doc_data)
        refresh_token = gen_token(doc_data)

        return ORJSONResponse(
            TokenDoctorsResponse(
                access_token=token,
                token_type="Bearer",
                doc=DoctorResponse(
                    id=user.id,
                    username=user.name,
                    last_name=user.last_name,
                    first_name=user.first_name,
                    dni=user.dni,
                    telephone=user.telephone,
                    email=user.email,
                    speciality_id=user.speciality_id,
                    is_active=user.is_active,
                    is_admin=user.is_admin,
                    is_superuser=user.is_superuser,
                    last_login=user.last_login,
                    date_joined=user.date_joined,
                ),
                refresh_token=refresh_token
            ).model_dump()
        )

    user_data = {
        "sub":str(user.id),
        "scopes":[]
    }

    if user.is_admin:
        user_data["scopes"].append("admin")

    if user.is_superuser:
        user_data["scopes"].append("superuser")
    else:
        user_data["scopes"].append("user")

    if user.is_active:
        user_data["scopes"].append("active")

    token = gen_token(user_data)
    refresh_token = gen_token(user_data, refresh=True)

    return ORJSONResponse(
        TokenUserResponse(
            access_token=token,
            token_type="bearer",
            refresh_token=refresh_token,
        ).model_dump()
    )

@router.delete("/logout")
async def logout(request: Request, authorization: Optional[str] = Header(None), _=Depends(auth)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No credentials provided or invalid format"
        )

    session_user = request.state.user

    token = authorization.split(" ")[1]

    table_name = "ban-token"

    if not storage.get(key=str(session_user.id), table_name="ban-token") is None:
        storage.update(key=str(session_user.id), value=token, table_name=table_name)

    result = storage.set(key=str(session_user.id), value=token, table_name=table_name)

    return result.model_dump()