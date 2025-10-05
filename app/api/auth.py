from fastapi import APIRouter, Request, Depends, HTTPException, Header, status, Form
from fastapi.responses import ORJSONResponse

from rich.console import Console

from typing import Optional, Dict, List, Annotated

from sqlmodel import select

from datetime import datetime

from app.models import Doctors, User
from app.db.main import SessionDep
from app.core.auth import gen_token, JWTBearer, decode, time_out
from app.core.interfaces.oauth import OauthRepository
from app.core.interfaces.users import UserRepository
from app.core.interfaces.emails import EmailService
from app.schemas.users import UserAuth
from app.schemas.auth import TokenUserResponse, TokenDoctorsResponse, OauthCodeInput
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
    """
    Obtiene los scopes/permisos del usuario autenticado.
    
    Retorna la lista de permisos y roles que tiene el usuario actual,
    útil para determinar qué acciones puede realizar en el frontend.
    
    Args:
        request (Request): Request con estado de autenticación
        _ (User): Usuario autenticado (inyectado por dependency)
        
    Returns:
        ORJSONResponse: Diccionario con lista de scopes del usuario
            - scopes (List[str]): Lista de permisos como ['admin', 'active', etc.]
            
    Note:
        Requiere autenticación válida. Los scopes se establecen durante login.
    """
    scopes = request.state.scopes
    return ORJSONResponse({
        "scopes":scopes,
    })

@router.post("/decode/")
async def decode_hex(data: OauthCodeInput):
    """
    Decodifica datos codificados en hexadecimal.
    
    Convierte códigos hexadecimales (típicamente de OAuth) de vuelta
    a su formato original legible.
    
    Args:
        data (OauthCodeInput): Objeto con código hexadecimal a decodificar
            - code (str): String en formato hexadecimal
            
    Returns:
        dict: Datos decodificados en formato original
        
    Note:
        Utiliza la función decode del sistema de autenticación para
        convertir bytes hexadecimales de vuelta a objetos Python.
    """
    bytes_code = bytes.fromhex(data.code)
    return decode(bytes_code, dict)

@router.post("/doc/login", response_model=TokenDoctorsResponse)
@time_out(10)
async def doc_login(session: SessionDep, credentials: Annotated[DoctorAuth, Form(...)]):
    """
    Autentica médicos en el sistema.
    
    Procesa credenciales de login específicas para médicos, validando
    email y contraseña, y generando tokens JWT con scopes apropiados.
    
    Args:
        session (SessionDep): Sesión de base de datos
        credentials (DoctorAuth): Credenciales del médico desde formulario
            - email (str): Email del médico
            - password (str): Contraseña del médico
            
    Returns:
        ORJSONResponse: Respuesta con tokens y datos del médico
            - access_token (str): JWT para autenticación
            - token_type (str): Tipo de token (Bearer)
            - doc (DoctorResponse): Información completa del médico
            - refresh_token (str): Token para renovación
            
    Raises:
        HTTPException: 404 si credenciales inválidas
        
    Note:
        - Rate limited: máximo 1 intento cada 10 segundos
        - Actualiza last_login automáticamente
        - Scopes: ['doc'] + ['active'] si está activo
    """
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
    refresh_token = gen_token(doc_data, refresh=True)
    
    doc.last_login = datetime.now()

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
                address=doc.address
            ),
            refresh_token=refresh_token
        ).model_dump()
    )

@router.post("/login", response_model=TokenUserResponse)
@time_out(10)
async def login(session: SessionDep, credentials: Annotated[UserAuth, Form(...)]):
    """
    Autentica usuarios regulares del sistema.
    
    Procesa credenciales de login para usuarios, validando email y contraseña,
    y generando tokens JWT con scopes basados en el rol del usuario.
    
    Args:
        session (SessionDep): Sesión de base de datos
        credentials (UserAuth): Credenciales del usuario desde formulario
            - email (str): Email del usuario
            - password (str): Contraseña del usuario
            
    Returns:
        ORJSONResponse: Respuesta con tokens de autenticación
            - access_token (str): JWT para autenticación (15 min)
            - token_type (str): Tipo de token (Bearer)
            - refresh_token (str): Token para renovación (24 horas)
            
    Raises:
        HTTPException: 404 si email no existe
        HTTPException: 400 si contraseña incorrecta
        
    Note:
        - Rate limited: máximo 1 intento cada 10 segundos
        - Scopes asignados según rol:
          * 'admin' para administradores
          * 'superuser' para superusuarios
          * 'user' para usuarios regulares
          * 'active' si cuenta está activa
        - Actualiza timestamp de last_login
    """
    console.print(credentials)
    statement = select(User).where(User.email == credentials.email)
    result = session.exec(statement)
    user: User = result.first()
    console.print(user)
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
    """
    Inicia el flujo de autenticación OAuth con servicios externos.
    
    Redirige al usuario al servicio OAuth especificado para autenticación.
    Actualmente soporta Google OAuth.
    
    Args:
        service (str): Nombre del servicio OAuth ('google')
        
    Returns:
        RedirectResponse: Redirección al proveedor OAuth
        
    Raises:
        HTTPException: 501 si el servicio no está implementado
        HTTPException: 500 para errores del servicio OAuth
        
    Note:
        El usuario será redirigido al proveedor OAuth y luego de vuelta
        al callback webhook para completar la autenticación.
    """
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
    """
    Maneja la respuesta del callback de Google OAuth.
    
    Procesa el código de autorización devuelto por Google, crea o autentica
    al usuario, y envía emails de notificación apropiados.
    
    Args:
        request (Request): Request con parámetros de query de Google
            - code (str): Código de autorización de Google
            
    Returns:
        RedirectResponse: Respuesta del repositorio OAuth
        
    Raises:
        HTTPException: 500 para errores en el procesamiento
        
    Note:
        - Para usuarios nuevos: envía email de bienvenida + credenciales
        - Para usuarios existentes: completa autenticación
        - Las credenciales temporales usan el ID de Google como contraseña
    """
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
async def refresh(request: Request, user: User = Depends(auth)):
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
        
    if "google" in request.state.scopes:
        user_data["scopes"].append("google")

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
    """
    Cierra la sesión del usuario invalidando su token.
    
    Añade el token actual a una lista de tokens baneados para prevenir
    su reutilización, efectivamente cerrando la sesión de manera segura.
    
    Args:
        request (Request): Request con información del usuario autenticado
        authorization (str, optional): Header Authorization con el token
        _ (User): Usuario autenticado (inyección de dependencia)
        
    Returns:
        dict: Confirmación del logout con detalles del almacenamiento
        
    Raises:
        HTTPException: 403 si no hay credenciales o formato inválido
        
    Note:
        - El token queda permanentemente invalidado
        - Se almacena en tabla 'ban-token' del storage
        - Actualiza registro existente si el usuario ya tenía tokens baneados
    """
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