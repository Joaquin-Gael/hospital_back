from fastapi import APIRouter, Request, Depends, HTTPException, Header, status, Form, Cookie
from fastapi.responses import ORJSONResponse

from rich.console import Console

from typing import Optional, Dict, List, Annotated

from sqlmodel import select

from datetime import datetime
from uuid import UUID

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
from app.config import token_expire_minutes, token_refresh_expire_days

from app.audit import (
    AuditAction,
    AuditEmitter,
    AuditEventCreate,
    AuditSeverity,
    AuditTargetType,
    build_request_metadata,
    get_audit_emitter,
    get_request_identifier,
)

console = Console()

auth = JWTBearer()


def _make_event(
    request: Request,
    *,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    target_type: AuditTargetType = AuditTargetType.WEB_SESSION,
    actor_id: Optional[UUID] = None,
    target_id: Optional[UUID] = None,
    details: Optional[Dict[str, object]] = None,
) -> AuditEventCreate:
    return AuditEventCreate(
        action=action,
        severity=severity,
        target_type=target_type,
        actor_id=actor_id,
        target_id=target_id,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
        details=dict(details or {}),
    )


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

oauth_router = APIRouter(
    prefix="/oauth",
    tags=["oauth"]
)

@router.get("/scopes", response_model=Dict[str, List[str]])
async def get_scopes(request: Request, user: User | Doctors = Depends(auth)):
    """
    Obtiene los scopes/permisos del usuario autenticado.
    
    Retorna la lista de permisos y roles que tiene el usuario actual,
    útil para determinar qué acciones puede realizar en el frontend.
    
    Args:
        request (Request): Request con estado de autenticación
        user (User | Doctors): Usuario autenticado (inyectado por dependency)
        
    Returns:
        ORJSONResponse: Diccionario con lista de scopes del usuario
            - scopes (List[str]): Lista de permisos como ['admin', 'active', etc.]
            
    Note:
        Requiere autenticación válida. Los scopes se establecen durante login.
    """
    # Los scopes se establecen en request.state por el JWTBearer
    # pero para asegurarnos, también los extraemos del usuario
    scopes = getattr(request.state, 'scopes', None)
    
    # Si por alguna razón no están en request.state, construirlos desde el usuario
    if scopes is None:
        scopes = []
        
        if isinstance(user, Doctors):
            scopes.append("doc")
            if user.is_active:
                scopes.append("active")
        else:  # Es un User
            if user.is_admin:
                scopes.append("admin")
            if user.is_superuser:
                scopes.append("superuser")
            else:
                scopes.append("user")
            if user.is_active:
                scopes.append("active")
    
    return ORJSONResponse({
        "scopes": scopes,
    })

@router.post("/decode/")
@time_out(10)
async def decode_hex(request: Request, data: OauthCodeInput):
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
async def doc_login(
    request: Request,
    session: SessionDep,
    credentials: Annotated[DoctorAuth, Form(...)],
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
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
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.USER_LOGIN_FAILED,
                severity=AuditSeverity.WARNING,
                details={"email": credentials.email, "role": "doctor", "reason": "not_found"},
            )
        )
        raise HTTPException(status_code=404, detail="Invalid credentials")

    if not doc.check_password(credentials.password):
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.USER_LOGIN_FAILED,
                severity=AuditSeverity.WARNING,
                actor_id=doc.id,
                details={"email": credentials.email, "role": "doctor", "reason": "invalid_password"},
            )
        )
        raise HTTPException(status_code=404, detail="Invalid credentials")

    doc_data = {
        "sub":str(doc.id),
        "scopes":["doc"]
    }

    if doc.is_active:
        doc_data["scopes"].append("active")

    token = gen_token(doc_data)
    refresh_token = gen_token(doc_data, refresh=True)

    try:
        record = doc.mark_login(actor_id=doc.id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    session.add(doc)
    session.commit()
    session.refresh(doc)

    await emitter.emit_record(
        record,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
    )

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.TOKEN_ISSUED,
            target_type=AuditTargetType.AUTH_TOKEN,
            actor_id=doc.id,
            target_id=doc.id,
            details={"scopes": doc_data["scopes"], "refresh": True},
        )
    )
    
    response = ORJSONResponse(
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
    
    response.set_cookie(
        key="authorization",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=token_expire_minutes * 60
    )
    
    response.set_cookie(
        key="authorization_refresh",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=token_refresh_expire_days * 24 * 60 * 60
    )
    

    return response

@router.post("/login", response_model=TokenUserResponse)
@time_out(10)
async def login(
    request: Request,
    session: SessionDep,
    credentials: Annotated[UserAuth, Form(...)],
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
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
    #console.print(credentials)
    statement = select(User).where(User.email == credentials.email)
    result = session.exec(statement)
    user: User = result.first()
    #console.print(user)
    if not user:
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.USER_LOGIN_FAILED,
                severity=AuditSeverity.WARNING,
                details={"email": credentials.email, "role": "user", "reason": "not_found"},
            )
        )
        raise HTTPException(status_code=404, detail="Invalid credentials payload")

    if not user.check_password(credentials.password):
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.USER_LOGIN_FAILED,
                severity=AuditSeverity.WARNING,
                actor_id=user.id,
                details={"email": credentials.email, "role": "user", "reason": "invalid_password"},
            )
        )
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

    try:
        record = user.mark_login(actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    session.add(user)
    session.commit()
    session.refresh(user)

    await emitter.emit_record(
        record,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
    )

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.TOKEN_ISSUED,
            target_type=AuditTargetType.AUTH_TOKEN,
            actor_id=user.id,
            target_id=user.id,
            details={"scopes": user_data["scopes"], "refresh": True},
        )
    )

    response = ORJSONResponse(
        TokenUserResponse(
            access_token=token,
            token_type="Bearer",
            refresh_token=refresh_token,
        ).model_dump()
    )
    
    response.set_cookie(
        key="authorization",
        value=token,
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=token_expire_minutes * 60
    )
    
    response.set_cookie(
        key="authorization_refresh",
        value=refresh_token,
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=token_refresh_expire_days * 24 * 60 * 60
    )

    return response

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
async def google_callback(request: Request, emitter: AuditEmitter = Depends(get_audit_emitter)):
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
        data, exist, audit, response = OauthRepository.google_callback(params.get("code"))
        await emitter.emit_record(
            audit,
            request_id=get_request_identifier(request),
            request_metadata=build_request_metadata(request),
        )
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.TOKEN_ISSUED,
                target_type=AuditTargetType.AUTH_TOKEN,
                actor_id=audit.actor_id,
                target_id=audit.target_id,
                details={"scopes": ["google", "user"], "refresh": False},
            )
        )
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
async def refresh(
    request: Request,
    user: User = Depends(auth),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    if isinstance(user, Doctors):
        doc_data = {
            "sub":str(user.id),
            "scopes":["doc"]
        }

        if user.is_active:
            doc_data["scopes"].append("active")


        token = gen_token(doc_data)
        refresh_token = gen_token(doc_data)

        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.TOKEN_ISSUED,
                target_type=AuditTargetType.AUTH_TOKEN,
                actor_id=user.id,
                target_id=user.id,
                details={"scopes": doc_data["scopes"], "refresh": True},
            )
        )

        response = ORJSONResponse(
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
        
        response.set_cookie(
            key="authorization",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=token_expire_minutes * 60
        )
    
        response.set_cookie(
            key="authorization_refresh",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=token_refresh_expire_days * 24 * 60 * 60
        )
        
        return response

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

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.TOKEN_ISSUED,
            target_type=AuditTargetType.AUTH_TOKEN,
            actor_id=user.id,
            target_id=user.id,
            details={"scopes": user_data["scopes"], "refresh": True},
        )
    )

    response = ORJSONResponse(
        TokenUserResponse(
            access_token=token,
            token_type="bearer",
            refresh_token=refresh_token,
        ).model_dump()
    )
    
    response.set_cookie(
            key="authorization",
            value=token,
            httponly=False,
            secure=False,
            samesite="lax",
            max_age=token_expire_minutes * 60
        )
    
    response.set_cookie(
            key="authorization_refresh",
            value=refresh_token,
            httponly=False,
            secure=False,
            samesite="lax",
            max_age=token_refresh_expire_days * 24 * 60 * 60
        )
        
    return response

@router.delete("/logout")
async def logout(
    request: Request,
    authorization: Optional[str] = Cookie(None),
    _: User = Depends(auth),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
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
    
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No credentials provided or invalid format"
        )
    
    
    token = authorization

    session_user = request.state.user

    table_name = "ban-token"

    if not storage.get(key=str(session_user.id), table_name="ban-token") is None:
        storage.update(key=str(session_user.id), value=token, table_name=table_name)

    result = storage.set(key=str(session_user.id), value=token, table_name=table_name)

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.TOKEN_REVOKED,
            target_type=AuditTargetType.AUTH_TOKEN,
            actor_id=session_user.id,
            target_id=session_user.id,
            severity=AuditSeverity.INFO,
            details={"table": table_name},
        )
    )

    response = ORJSONResponse(
        result.model_dump()
        )
    
    response.delete_cookie(
            key="authorization",
            httponly=True,
            secure=True,
            samesite="strict",
        )
    
    response.delete_cookie(
            key="authorization_refresh",
            httponly=True,
            secure=True,
            samesite="strict",
        )
    
    return response