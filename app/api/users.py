from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, UploadFile
from fastapi.responses import ORJSONResponse

from sqlalchemy import select

from typing import List, Annotated

from rich.console import Console

from datetime import datetime

from collections import defaultdict

from pathlib import Path

from uuid import UUID

import asyncio   

import logging

import sys

import tempfile

import re

import secrets

import string

import PIL

import pytesseract

import numpy as np

import cv2

import magic

from app.schemas.medica_area import HealthInsuranceBase
from app.schemas.users import UserRead, UserCreate, UserDelete, UserUpdate, UserPasswordUpdate, \
    UserPetitionPasswordUpdate, DniForm
from app.models import User, HealthInsurance
from app.core.auth import JWTBearer
from app.db.main import SessionDep
from app.core.interfaces.emails import EmailService
from app.core.interfaces.users import UserRepository
from app.core.auth import encode, decode
from app.storage import storage
from app.config import cors_host, email_host_user, binaries_dir

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
handler.setFormatter(formatter)

logger.addHandler(handler)

TESS_DIGITS = "-c tessedit_char_whitelist=0123456789 --oem 3"

pytesseract.pytesseract.tesseract_cmd = binaries_dir / "tesseract.exe"

console = Console()

auth = JWTBearer()

private_router = APIRouter(
    dependencies=[
        Depends(auth)
    ],
    redirect_slashes=True,
)

public_router = APIRouter(
    redirect_slashes=True,
)

@private_router.get("/", response_model=List[UserRead])
async def get_users(session: SessionDep):
    """
    Obtiene lista completa de todos los usuarios del sistema.
    
    Recupera todos los usuarios registrados con su información completa,
    incluyendo datos personales, estado de activación y seguros médicos.
    
    Args:
        session (SessionDep): Sesión de base de datos inyectada
        
    Returns:
        ORJSONResponse: Lista de usuarios serializados con campos:
            - id, is_active, is_admin, is_superuser
            - last_login, date_joined
            - username, email, first_name, last_name
            - dni, address, telephone, blood_type
            - img_profile, health_insurance
            
    Note:
        Requiere autenticación. Incluye logs de debug para troubleshooting.
    """
    statement = select(User).where(True)
    result: List[User] = session.exec(statement).scalars().all()
    users = []
    console.print(result)
    console.print(User.__table__)
    for user in result:
        console.print(user)
        try:
            console.print(user.id)
        except Exception:
            console.print_exception(show_locals=True)
        users.append(
            UserRead(
                id=user.id,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                date_joined=user.date_joined,
                username=user.name,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                dni=user.dni,
                address=user.address,
                telephone=user.telephone,
                blood_type=user.blood_type,
                img_profile=user.url_image_profile
            ).model_dump()
        )

    return ORJSONResponse(users)

@private_router.get("/{user_id}/")
async def get_user_by_id(session: SessionDep, user_id: UUID):
    """
    Obtiene información detallada de un usuario específico por su ID.
    
    Recupera un usuario individual con toda su información personal,
    incluyendo seguros médicos asociados.
    
    Args:
        session (SessionDep): Sesión de base de datos inyectada
        user_id (UUID): Identificador único del usuario
        
    Returns:
        ORJSONResponse: Datos completos del usuario encontrado
        
    Raises:
        HTTPException: 404 si el usuario no existe
        
    Note:
        Requiere autenticación válida.
    """
    user: User = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")

    return ORJSONResponse(
        UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            blood_type=user.blood_type,
            address=user.address,
            telephone=user.telephone,
            img_profile=user.url_image_profile,
            health_insurance=user.health_insurance
        ).model_dump()
    )

@private_router.get("/me", response_model=UserRead)
async def me_user(request: Request, session: SessionDep):
    """
    Obtiene el perfil del usuario autenticado actualmente.
    
    Retorna la información completa del usuario que está autenticado
    en la sesión actual, actualizando y refrescando los datos.
    
    Args:
        request (Request): Request HTTP con estado de autenticación
        session (SessionDep): Sesión de base de datos inyectada
        
    Returns:
        ORJSONResponse: Perfil completo del usuario autenticado
        
    Raises:
        HTTPException: 401 si no está autenticado o token inválido
        
    Note:
        Realiza merge y refresh del usuario para datos actualizados.
    """
    user: User = request.state.user

    if not isinstance(user, User):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Not authorized: {user}")

    user = session.merge(user)
    session.commit()
    session.refresh(user)

    return ORJSONResponse({
        "user":UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            telephone=user.telephone,
            blood_type=user.blood_type,
            address=user.address,
            img_profile=user.url_image_profile,
            health_insurance=[h.id for h in user.health_insurance]
        ).model_dump(),
    })

@public_router.post("/add/", response_model=UserRead)
async def add_user(session: SessionDep, user: Annotated[UserCreate, Form(...)]):
    """
    Registra un nuevo usuario en el sistema.
    
    Crea una nueva cuenta de usuario con los datos proporcionados,
    incluyendo hasheo seguro de contraseña y manejo de imagen de perfil.
    
    Args:
        session (SessionDep): Sesión de base de datos inyectada
        user (UserCreate): Datos del usuario desde formulario
        
    Returns:
        ORJSONResponse: Usuario creado con información básica
        
    Raises:
        HTTPException: 400 si hay errores en los datos o creación
        
    Note:
        - Endpoint público (no requiere autenticación)
        - Hashea automáticamente la contraseña
        - Maneja imagen de perfil opcional
        - Incluye seguros médicos en la respuesta
    """
    try:
        user_db = User(
            email=user.email,
            name=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            address=user.address,
            telephone=user.telephone,
            blood_type=user.blood_type
        )
        user_db.set_password(user.password)
        await user_db.save_profile_image(user.img_profile) if user.img_profile else None
        session.add(user_db)
        session.commit()
        session.refresh(user_db)
        return ORJSONResponse(
            UserRead(
                id=user_db.id,
                is_active=user_db.is_active,
                is_admin=user_db.is_admin,
                is_superuser=user_db.is_superuser,
                last_login=user_db.last_login,
                date_joined=user_db.date_joined,
                username=user_db.name,
                email=user_db.email,
                first_name=user_db.first_name,
                last_name=user_db.last_name,
                dni=user_db.dni,
                address=user_db.address,
                telephone=user_db.telephone,
                blood_type=user_db.blood_type,
                img_profile=user_db.url_image_profile,
                health_insurance=[h.id for h in user_db.health_insurance]
            ).model_dump()
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        return ORJSONResponse({"error": str(e)}, status_code=400)
    
@private_router.post("/verify/dni")
async def verify_dni(request: Request, dni_form: Annotated[DniForm, Form(...)], session: SessionDep):
    """
    Endpoint para extraer número de DNI de fotos del frente y dorso.
    
    Recibe dos imágenes (frente y dorso del DNI) y devuelve el número
    encontrado usando OCR con múltiples estrategias de extracción.
    
    Args:
        dni_form: Form con campos 'front' y 'back' (archivos de imagen)
        
    Returns:
        dict: {
            "dni": str o None - El DNI más confiable encontrado,
        }
    """
    try:    
        #console.print(dni_form.front.content_type, dni_form.back.content_type)
        
        if not dni_form.front.content_type.startswith("image/") or not dni_form.back.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Files must be images")

        b1 = await dni_form.front.read()
        b2 = await dni_form.back.read()
        
        if len(b1) > 8_000_000 or len(b2) > 8_000_000:
            raise HTTPException(status_code=400, detail="Images must be smaller than 8MB")
        
        if not magic.from_buffer(b1, mime=True) in ['image/jpeg', 'image/png'] or not magic.from_buffer(b2, mime=True) in ['image/jpeg', 'image/png']:
            raise HTTPException(status_code=400, detail="Files must be JPEG or PNG images")
        
        img_size = (1500, 1000)

        def bytes_to_cv2(b):
            """
            Convierte bytes de imagen a formato OpenCV.
            
            Toma datos binarios de una imagen y los convierte al formato
            que OpenCV puede procesar para manipulación de imágenes.
            
            Args:
                b (bytes): Datos binarios de la imagen
                
            Returns:
                numpy.ndarray: Imagen en formato OpenCV (BGR)
                
            Raises:
                ValueError: Si cv2 no puede decodificar la imagen
            """
            arr = np.frombuffer(b, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("cv2 no pudo decodificar la imagen")
            return img

        img1 = bytes_to_cv2(b1)
        img2 = bytes_to_cv2(b2)

        def extract_from_mrz(img_color, size: tuple[int, int]):
            """
            Extrae números de DNI de la zona MRZ (Machine Readable Zone).
            
            Busca en la zona MRZ del documento de identidad, que son las líneas
            inferiores con caracteres especiales y '<<'. Esta zona suele contener
            el DNI de forma más confiable que el texto impreso normal.
            
            Args:
                img_color (numpy.ndarray): Imagen en color del documento
                size (tuple): Tupla con (ancho, alto) para redimensionar
                
            Returns:
                tuple: (lista_de_dnis_encontrados, texto_mrz_completo)
                    - lista de strings con DNIs de 8 dígitos
                    - texto completo extraído de la zona MRZ
                    
            Note:
                Aplica filtros de nitidez y busca patrones específicos:
                - Secuencias de 8 dígitos
                - Formato XX.XXX.XXX
                - Líneas con '<<' (características de MRZ)
            """
            img = cv2.resize(img_color, size)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            matriz = np.array([
                [0,-1,0],
                [-1,5,-1],
                [0,-1,0]
            ])
            
            gray = cv2.filter2D(src=gray, ddepth=0, kernel=matriz)
            
            # OCR sin restricciones para capturar toda la MRZ
            mrz_text = pytesseract.image_to_string(gray, config="--psm 6")
            
            # Buscar líneas típicas de MRZ (tienen '<<' y son largas)
            mrz_candidates = re.findall(r'.{10,}\<\<.{2,}', mrz_text.replace('\n',' '))
            digits = []
            
            # En las líneas MRZ buscar secuencias de 8 dígitos
            for m in mrz_candidates:
                digits += re.findall(r'\d{8}', m)
                
            if not digits:
                for m in mrz_candidates:
                    digits += re.findall(r'\d{2}\.\d{3}\.\d{3}')
                
            # Si no encontramos nada específico, buscar en todo el texto
            if not digits:
                digits += re.findall(r'\d{8}', mrz_text)
                
            # Eliminar duplicados manteniendo el orden
            return list(dict.fromkeys(digits)), mrz_text

        mrz1, mrz_text1 = extract_from_mrz(img1, img_size)
        mrz2, mrz_text2 = extract_from_mrz(img2, img_size)
        
        
        if not mrz1:
            console.print(f"lista de valores 1: {mrz1}")
            for _ in range(5):
                mrz1, mrz_text1 = extract_from_mrz(img1, img_size)
                
        if not mrz2:
            console.print(f"lista de valores 2: {mrz2}")
            for _ in range(5):
                mrz2, mrz_text2 = extract_from_mrz(img2, img_size)
                
                
        console.print(mrz_text1)

        if not mrz1 and not mrz2:
            raise HTTPException(status_code=400, detail="No DNI found in images")

        user = request.state.user
        user.dni = mrz1[0]
        session.commit()

        return {
            "dni":[mrz1, mrz2],
        }

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=400, detail=f"Invalid images or OCR error: {str(e)}")

@private_router.delete("/delete/{user_id}/", response_model=UserDelete)
async def delete_user(request: Request, user_id: UUID, session: SessionDep):
    """
    Elimina permanentemente un usuario del sistema.
    
    Borra completamente un usuario de la base de datos. Solo los superusuarios
    pueden realizar esta acción y no pueden eliminar su propia cuenta.
    
    Args:
        request (Request): Request con información de autenticación
        user_id (UUID): ID del usuario a eliminar
        session (SessionDep): Sesión de base de datos
        
    Returns:
        ORJSONResponse: Confirmación de eliminación con datos del usuario eliminado
        
    Raises:
        HTTPException: 403 si no tiene permisos o intenta eliminarse a sí mismo
        HTTPException: 404 si el usuario no existe
        
    Warning:
        Esta operación es irreversible y eliminará todos los datos asociados.
    """
    if not request.state.user.is_superuser or str(request.state.user.id) == user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        user: User = session.get(User, user_id)

        session.delete(user)
        session.commit()
        user_deleted = UserDelete(
            id=user.id,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
        )
        return ORJSONResponse(user_deleted.model_dump())
    except Exception:
        console.print_exception(show_locals=True)
        return ORJSONResponse({"error": "User not found"}, status_code=404)

@private_router.patch("/update/{user_id}/", response_model=UserRead)
async def update_user(request: Request, user_id: UUID, session: SessionDep, user_form: Annotated[UserUpdate, Form(...)]):

    if not request.state.user.id == user_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un unauthorized")

    user: User = session.get(User, user_id)

    console.print(user_form.health_insurance)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    form_fields: List[str] = user_form.__fields__.keys()

    for field in form_fields:
        value = getattr(user_form, field, None)
        if not field in ["username", "health_insurance", "img_profile"] and value is not None and not value in ["", " "]:
            setattr(user, field, value)
        elif field == "username" and value is not None and not value in ["", " "]:
            if not value:
                raise HTTPException(status_code=400, detail="Username cannot be empty")
            user.name = user_form.username
        elif field  == "health_insurance" and value is not None:
            for health_insurance_i in user_form.health_insurance:
                health_insurance_oj = session.get(HealthInsurance, health_insurance_i)
                if not health_insurance_oj in user.health_insurance:
                    user.health_insurance.append(health_insurance_oj)
            else:
                continue
        else:
            continue

    if user_form.img_profile and not "google" in request.state.scopes:
        await user.save_profile_image(user_form.img_profile)

    session.add(user)
    session.commit()
    session.refresh(user)

    return ORJSONResponse(
        UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            blood_type=user.blood_type,
            img_profile=user.url_image_profile,
            health_insurance=[h.id for h in user.health_insurance]

        ).model_dump()
    )

@public_router.post("/update/petition/password")
async def update_petition_password(session: SessionDep, data: Annotated[UserPetitionPasswordUpdate, Form(...)]):
    try:
        user: User = session.exec(
            select(User).where(User.email == data.email)
        ).first()[0]

        if not user:
            ORJSONResponse({"detail": "Ok 200"}, status_code=200)
            
        code = [secrets.choice(string.ascii_letters + string.digits) for _ in range(6)]

        r_cod = "".join(code)
        
        console.print(f"User: {user} - Date Type: {type(user)}")
        
        r_code_data = {
            "user": str(user.id),
            "r_cod": r_cod,
            "state": False
        }

        storage.set(key=user.email, value=r_code_data, table_name="recovery-codes", short_live=True)

        EmailService.send_password_reset_email(user.email, reset_code=r_cod)

    except Exception:
        console.print_exception(show_locals=True)
        return ORJSONResponse({"detail":"Ok 200"}, status_code=200)
    
@public_router.post("update/verify/code")
async def verify_code(session: SessionDep, email: str = Form(...), code: str = Form(...)):
    try:
        # Usar scalar_one_or_none para obtener un objeto User directo o None
        user = session.scalar(
            select(User).where(User.email == email)
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        code_storage = storage.get(key=user.email, table_name="recovery-codes")
        
        if not code_storage or code_storage.value.value["r_cod"] != code or code_storage.value.expired <= datetime.now():
            raise HTTPException(status_code=400, detail="Invalid code")
        
        code_storage.value.value["state"] = True
        
        return {"message": "Code verified successfully", "success": True}
    
    except HTTPException:
        # Re-lanzar HTTPExceptions (404, 400) sin modificar
        raise
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@public_router.post("/update/confirm/password", response_model=UserRead)
async def update_confirm_password(session: SessionDep, email: str = Form(...), code: str = Form(...), new_password: str = Form(...)):
    try:
        user: User = session.exec(
            select(User).where(User.email == email)
        ).first()[0]

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        code_storage = storage.get(key=user.email, table_name="recovery-codes")
        
        if not code_storage.value.value["state"]:
            raise HTTPException(status_code=401, detail="Unautorized")

        if not code_storage or code_storage.value.value["r_cod"] != code or code_storage.value.expired <= datetime.now():
            raise HTTPException(status_code=400, detail="Invalid code")

        user.set_password(new_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        
        EmailService.send_password_changed_notification_email(
            user.email,
            help_link=f"{cors_host}/support",
            contact_email=email_host_user,
            contact_number="1234567890"
        )

        return ORJSONResponse(
            UserRead(
                id=user.id,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                date_joined=user.date_joined,
                username=user.name,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                dni=user.dni,
                blood_type=user.blood_type,
                img_profile=user.url_image_profile
            ).model_dump()
        )
    except HTTPException as he:
        raise he
    except Exception:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@private_router.patch("/update/{user_id}/password", response_model=UserRead)
async def update_user_password(request: Request, user_id: UUID, session: SessionDep, user_form: UserPasswordUpdate):

    if not request.state.user.id == user_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un unauthorized")

    user: User = session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.check_password(user_form.old_password) or not user_form.new_password == user_form.new_password_confirm:
        raise HTTPException(status_code=404, detail="User not found")

    user.set_password(user_form.new_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    EmailService.send_password_changed_notification_email(
        user.email,
        help_link="https://support.google.com/accounts/answer/41078?hl=en",
        contact_email="email@email.com",
        contact_number="1234567890"
    )

    return ORJSONResponse(
        UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            blood_type=user.blood_type,
            telephone=user.telephone,
            address=user.address,
            img_profile=user.url_image_profile,
        ).model_dump()
    )

@private_router.patch("/ban/{user_id}/", response_model=UserRead)
async def ban_user(request: Request, user_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    user: User = session.get(User, user_id)

    user.is_active = True
    session.commit()
    session.refresh(user)

    return ORJSONResponse({
        "user":UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            blood_type=user.blood_type,
            img_profile=user.url_image_profile
        ),
        "message":f"User {user.name} has been banned."
    })

@private_router.patch("/unban/{user_id}/", response_model=UserRead)
async def unban_user(request: Request, user_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    user: User = session.get(User, user_id)

    user.is_banned = False
    session.commit()
    session.refresh(user)

    return ORJSONResponse({
        "user":UserRead(
            id=user.id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            username=user.name,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            dni=user.dni,
            blood_type=user.blood_type,
            img_profile=user.url_image_profile
        ),
        "message":f"User {user.name} has been unbanned."
    })

router = APIRouter(
    tags=["users"],
    prefix="/users",
    default_response_class=ORJSONResponse,
)

router.include_router(private_router)
router.include_router(public_router)