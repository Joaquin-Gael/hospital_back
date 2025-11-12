import jwt
from jwt import PyJWTError

from datetime import datetime, timedelta
import time

from pydantic import BaseModel

from fastapi import Header, HTTPException, status, Request, WebSocket

from functools import singledispatch, wraps

from sqlmodel import select

from typing import Optional, Any, Type, TypeVar, Callable, ParamSpec

from cryptography.fernet import Fernet

from json import loads, dumps, JSONDecodeError

from uuid import UUID

from rich.console import Console

from app.config import token_key, api_name, version, debug
from app.models import Doctors, User
from app.db.session import session_factory
from app.storage import storage
from app.core.interfaces.emails import EmailService
from app.storage import storage
from app.audit import (
    AuditAction,
    AuditEventCreate,
    AuditSeverity,
    AuditTargetType,
    build_request_metadata,
    get_audit_emitter,
    get_request_identifier,
)

encoder_key = Fernet.generate_key()

encoder_f = Fernet(encoder_key)

console = Console()


async def _emit_security_event(
    request: Request,
    *,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    details: Optional[dict] = None,
    actor_id: Optional[UUID] = None,
    target_id: Optional[UUID] = None,
    target_type: AuditTargetType = AuditTargetType.WEB_SESSION,
) -> None:
    emitter = get_audit_emitter()
    event = AuditEventCreate(
        action=action,
        severity=severity,
        target_type=target_type,
        actor_id=actor_id,
        target_id=target_id,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
        details=dict(details or {}),
    )
    try:
        await emitter.emit_event(event)
    except Exception:  # pragma: no cover - defensive logging
        if debug:
            console.print_exception(show_locals=True)


@singledispatch
def encode(data: object) -> bytes:
    """
    Codifica datos de forma segura usando encriptación simétrica.
    
    Función polimórfica que puede manejar diferentes tipos de datos,
    serializándolos a JSON cuando sea necesario y encriptándolos con Fernet.
    
    Args:
        data (object): Datos a codificar (cualquier tipo Python)
        
    Returns:
        bytes: Datos encriptados
        
    Raises:
        TypeError: Si el tipo de datos no es serializable
        
    Note:
        Esta es la implementación base que usa singledispatch.
        Hay implementaciones específicas para cada tipo de dato.
    """
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
    text = dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
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
    """
    Decodifica datos encriptados con tipo específico opcional.
    
    Desencripta datos usando Fernet y opcionalmente los convierte al tipo
    especificado, incluyendo validación con Pydantic para modelos.
    
    Args:
        data (bytes): Datos encriptados a decodificar
        dtype (Type[T], optional): Tipo esperado del resultado
        
    Returns:
        T | Any: Datos decodificados, opcionalmente convertidos al tipo especificado
        
    Raises:
        ValueError: Si el token es inválido o ha expirado
        ValidationError: Si la validación de Pydantic falla
        
    Note:
        - Si dtype es None, retorna el objeto Python nativo
        - Para BaseModel, usa model_validate() de Pydantic
        - Para tipos básicos (dict, list, etc.), hace casting directo
    """
    try:
        plaintext: bytes = encoder_f.decrypt(data)
    except Exception as e:
        console.print_exception(show_locals=True) if debug else None
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
    """
    Genera tokens JWT para autenticación del sistema.
    
    Crea tokens JWT con payload personalizado, configurando automáticamente
    campos estándar como emisor, tiempo de emisión y expiración.
    
    Args:
        payload (dict): Datos del usuario y scopes a incluir en el token
        refresh (bool): Si True, genera token de larga duración para refresh
        
    Returns:
        str: Token JWT codificado
        
    Note:
        - Tokens normales: 15 minutos de duración
        - Refresh tokens: 24 horas de duración  
        - Incluye automáticamente iat (issued at) e iss (issuer)
        - Usa algoritmo HS256 con clave secreta del sistema
    """
    payload.setdefault("iat", datetime.now())
    payload.setdefault("iss", f"{api_name}/{version}")
    if refresh:
        payload["exp"] = int((datetime.now() + timedelta(days=1)).timestamp())
        payload.setdefault("type", "refresh_token")
    else:
        payload["exp"] = int((datetime.now() + timedelta(minutes=15)).timestamp())
    return jwt.encode(payload, token_key, algorithm="HS256")

def decode_token(token: str):
    """
    Decodifica y valida tokens JWT del sistema.
    
    Verifica la firma, validez temporal y formato de tokens JWT,
    extrayendo el payload si es válido.
    
    Args:
        token (str): Token JWT a decodificar
        
    Returns:
        dict: Payload del token con datos del usuario y scopes
        
    Raises:
        ValueError: Si el token es inválido, expirado o malformado
        
    Note:
        - Usa leeway de 20 segundos para tolerancia de tiempo
        - Valida con la clave secreta del sistema
        - Solo acepta algoritmo HS256
    """
    try:
        payload = jwt.decode(token, key=token_key, algorithms=["HS256"], leeway=20)
        return payload
    except PyJWTError as e:
        print(e) if debug else None
        raise ValueError("Value Not Found") from e

P = ParamSpec("P")
R = TypeVar("R")

def time_out(seconds: Optional[float] = 1.0, max_trys: Optional[int] = 5) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorador para implementar rate limiting por IP en endpoints.
    
    Limita la frecuencia de requests por dirección IP, previniendo ataques
    de fuerza bruta y abuso del sistema.
    
    Args:
        seconds (float): Tiempo mínimo en segundos entre requests
        max_trys (int): Número máximo de intentos permitidos
        
    Returns:
        Callable: Función decoradora que aplica rate limiting
        
    Raises:
        HTTPException: 429 Too Many Requests si se exceden los límites
        
    Note:
        - Rastrea último acceso por IP en memoria
        - Usa storage temporal para contar intentos fallidos
        - Cada IP tiene límites independientes
        - Útil para endpoints de login y operaciones sensibles
        
    Example:
        @time_out(10, 3)  # Max 3 intentos cada 10 segundos
        async def login_endpoint():
            pass
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Diccionario para almacenar el último tiempo de acceso por IP
        last_access = {}
        
        @wraps(func)
        async def wrapper(request: Request, *args: P.args, **kwargs: P.kwargs) -> R:
            # Obtener la IP del cliente
            client_ip = request.client.host
            current_time = time.time()
            current_try = storage.get(key=client_ip, table_name="ip-time-out")
            
            if current_try is not None:
                storage.set(key=client_ip, value={"current_try": 1, "max_trys": max_trys}, table_name="ip-time-out")
            elif isinstance(current_try, dict):
                if current_try.get("current_try", 0) >= current_try.get("max_trys", max_trys):
                    await _emit_security_event(
                        request,
                        action=AuditAction.RATE_LIMIT_TRIGGERED,
                        severity=AuditSeverity.WARNING,
                        details={"ip": client_ip, "reason": "max_attempts", "endpoint": request.url.path},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Has excedido el número máximo de intentos. Por favor espera {seconds} segundos antes de intentar de nuevo."
                    )
                else:
                    current_try["current_try"] += 1
                    storage.set(key=client_ip, value=current_try, table_name="ip-time-out")
            
            # Verificar si existe un acceso previo para esta IP
            if client_ip in last_access:
                time_elapsed = current_time - last_access[client_ip]
                # Si no ha pasado suficiente tiempo, lanzar una excepción
                if time_elapsed < seconds:
                    await _emit_security_event(
                        request,
                        action=AuditAction.RATE_LIMIT_TRIGGERED,
                        severity=AuditSeverity.WARNING,
                        details={
                            "ip": client_ip,
                            "reason": "cooldown",
                            "endpoint": request.url.path,
                            "remaining": round(seconds - time_elapsed, 2),
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Por favor espera {seconds - time_elapsed:.1f} segundos antes de hacer otra petición"
                    )
            
            # Actualizar el tiempo de último acceso
            last_access[client_ip] = current_time
            
            # Ejecutar la función original
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator



class JWTBearer:
    """
    Clase de autenticación JWT para requests HTTP.
    
    Maneja la extracción, validación y procesamiento de tokens JWT
    desde headers Authorization, cargando los datos del usuario
    autenticado en el estado de la request.
    
    Attributes:
        Ninguno - funciona como dependency callable
        
    Note:
        - Funciona como FastAPI Dependency
        - Soporta tanto usuarios como médicos
        - Valida tokens baneados
        - Establece user y scopes en request.state
    """
    
    async def __call__(self, request: Request, authorization: Optional[str] = Header(None)) -> User | Doctors | None:
        """
        Procesa autenticación JWT para una request HTTP.
        
        Extrae el token del header Authorization, lo valida, y carga
        los datos del usuario correspondiente en el estado de la request.
        
        Args:
            request (Request): Request HTTP de FastAPI
            authorization (str, optional): Header "Authorization: Bearer {token}"
            
        Returns:
            User | Doctors | None: Usuario o médico autenticado
            
        Raises:
            HTTPException: 403 si no hay credenciales o formato inválido
            HTTPException: 401 si token inválido, expirado o usuario no existe
            HTTPException: 403 si token está baneado
            
        Note:
            - Valida formato "Bearer {token}"
            - Previene uso de refresh tokens en endpoints normales
            - Maneja warnings para cuentas Google
            - Establece request.state.user y request.state.scopes
        """
        if authorization is None or not authorization.startswith("Bearer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No credentials provided or invalid format"
            )

        token = authorization.split(" ")[1]

        try:
            payload = decode_token(token)
        except ValueError as e:
            await _emit_security_event(
                request,
                action=AuditAction.TOKEN_INVALID,
                severity=AuditSeverity.WARNING,
                details={"reason": "invalid_or_expired", "token_prefix": token[:8]},
            )
            raise HTTPException(status_code=401, detail=e.args) from e

        if request.scope["route"].name != "refresh_token":
            #console.rule(request.scope["route"].name)
            #console.print(f"Se intento hacer el refresh: {payload}")
            if payload.get("type") == "refresh_token":
                await _emit_security_event(
                    request,
                    action=AuditAction.TOKEN_INVALID,
                    severity=AuditSeverity.WARNING,
                    details={"reason": "refresh_token_used", "route": request.scope["route"].name},
                )
                raise HTTPException(status_code=401, detail="No credentials provided or invalid format")

        user_id = payload.get("sub")

        ban_token = storage.get(key=payload.get("sub"), table_name="ban-token")

        #console.print(">>> ", ban_token, " <<<") if debug else None

        if ban_token is not None:
            #console.print(f"Token banned: {ban_token.value}") if debug else None
            stored_token = getattr(getattr(ban_token, "value", None), "value", None)
            if stored_token and token == stored_token:
                await _emit_security_event(
                    request,
                    action=AuditAction.TOKEN_REVOKED,
                    severity=AuditSeverity.WARNING,
                    actor_id=UUID(user_id) if user_id else None,
                    target_id=UUID(user_id) if user_id else None,
                    target_type=AuditTargetType.AUTH_TOKEN,
                    details={"reason": "banned_token"},
                )
                raise HTTPException(status_code=403, detail="Token banned")

        try:
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token payload")


            statement = select(User).where(User.id == user_id)

            if "doc" in payload.get("scopes"):
                statement = select(Doctors).where(Doctors.id == user_id)

            with session_factory() as session:
                user = session.exec(statement).first()

            if "google" in payload.get("scopes") and not "doc" in payload.get("scopes"):
                EmailService.send_warning_google_account(
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    created=user.date_joined,
                    to_delete=datetime.now() + timedelta(days=7)
                )

            request.state.user = user
            request.state.scopes = payload.get("scopes")

            return user

        except Exception as e:
            console.print(e) if debug else None
            raise HTTPException(status_code=401, detail="Invalid or expired token")

class JWTWebSocket:
    async def __call__(self, websocket: WebSocket) -> tuple[User | Doctors, list[str]] | tuple[None, None] | None:
        query = websocket.query_params

        #console.print(query)

        if not "token" in query.keys() or query.get("token") is None:
            #console.print(f"query: {query}")
            await websocket.close(1008, reason="No credentials provided or invalid format")
            return None

        if not query.get("token").startswith("Bearer_"):
            #console.print(f"query: {query}")
            await websocket.close(1008, reason="No credentials provided or invalid format")
            return None

        token = query.get("token").split("_")[1]
        #console.print(f"Tokwn jwt websocket: {token}")

        try:
            payload = decode_token(token)
            #console.print(f"Payload token: {payload}")

            user_id = payload.get("sub")

            if user_id is None:
                #console.print("user id: ", user_id)
                await websocket.close(1008, reason="Invalid token payload")
                return None

            statement = select(User).where(User.id == user_id)

            if "doc" in payload.get("scopes"):
                statement = select(Doctors).where(Doctors.id == user_id)

            with session_factory() as session:
                user = session.exec(statement).first()

            if "google" in payload.get("scopes") and not "doc" in payload.get("scopes"):
                EmailService.send_warning_google_account(
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    created=user.date_joined,
                    to_delete=datetime.now() + timedelta(days=7)
                )

            return user, payload.get("scopes")

        except ValueError:
            console.print_exception(show_locals=True)
            await websocket.close(1008, reason="Invalid o Expired Token")
            return None