from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, UploadFile
from fastapi.responses import ORJSONResponse
from json import dumps, loads

from sqlalchemy import select

from typing import List, Annotated, Optional, Tuple

from rich.console import Console

from datetime import datetime

from collections import Counter

from pathlib import Path

from uuid import UUID

import re

import secrets

import string

import pytesseract

import numpy as np

import cv2

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
from app.db.cache import redis_client as rc
from app.config import CORS_HOST, EMAIL_HOST_USER, BINARIES_DIR

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

TESS_DIGITS = "-c tessedit_char_whitelist=0123456789 --oem 3"

pytesseract.pytesseract.tesseract_cmd = BINARIES_DIR / "tesseract.exe"

console = Console()

auth = JWTBearer()

class DNIExtractor:
    """
    Extractor profesional de DNI con múltiples estrategias de OCR.
    
    Implementa técnicas avanzadas de procesamiento de imágenes y
    múltiples estrategias de extracción para maximizar la precisión.
    """
    
    def __init__(self, target_size: Tuple[int, int] = (1500, 1000)):
        self.target_size = target_size
        self.dni_pattern = re.compile(r'\b\d{8}\b')
        self.dni_formatted_pattern = re.compile(r'\b\d{2}[.\s]?\d{3}[.\s]?\d{3}\b')
        
    def preprocess_image(self, img: np.ndarray, strategy: str = 'basic') -> np.ndarray:
        """
        Preprocesa la imagen con diferentes estrategias.
        
        Args:
            img: Imagen en formato OpenCV (BGR)
            strategy: Estrategia de preprocesamiento
                - 'basic': Conversión a escala de grises básica
                - 'contrast': Mejora de contraste
                - 'adaptive': Umbralización adaptativa
                - 'denoise': Reducción de ruido
                - 'sharpen': Enfoque agresivo
                
        Returns:
            Imagen preprocesada en escala de grises
        """
        # Redimensionar si es necesario
        if img.shape[:2] != self.target_size[::-1]:
            img = cv2.resize(img, self.target_size)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if strategy == 'basic':
            return gray
            
        elif strategy == 'contrast':
            # Ecualización de histograma para mejorar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
            
        elif strategy == 'adaptive':
            # Umbralización adaptativa
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
        elif strategy == 'denoise':
            # Reducción de ruido + contraste
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(denoised)
            
        elif strategy == 'sharpen':
            # Enfoque agresivo con kernel personalizado
            kernel = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            sharpened = cv2.filter2D(gray, -1, kernel)
            # Mejorar contraste adicional
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            return clahe.apply(sharpened)
            
        return gray
    
    def correct_skew(self, img: np.ndarray) -> np.ndarray:
        """
        Corrige la inclinación de la imagen usando detección de líneas.
        
        Args:
            img: Imagen en escala de grises
            
        Returns:
            Imagen corregida
        """
        # Detección de bordes
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        
        # Detección de líneas con Hough Transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return img
        
        # Calcular ángulos predominantes
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            if abs(angle) < 45:  # Ignorar líneas muy inclinadas
                angles.append(angle)
        
        if not angles:
            return img
        
        # Usar la mediana de los ángulos
        median_angle = np.median(angles)
        
        # Solo rotar si el ángulo es significativo (> 0.5 grados)
        if abs(median_angle) < 0.5:
            return img
        
        # Rotar la imagen
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), 
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def extract_dni_region(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Intenta extraer solo la región del DNI/documento.
        
        Args:
            img: Imagen completa
            
        Returns:
            Región del documento recortada o imagen original si no se detecta
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # Detección de bordes
        edges = cv2.Canny(gray, 50, 150)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return img
        
        # Buscar el contorno más grande (probablemente el documento)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Calcular el área del contorno
        area = cv2.contourArea(largest_contour)
        img_area = gray.shape[0] * gray.shape[1]
        
        # Si el contorno es muy pequeño, devolver imagen original
        if area < img_area * 0.1:
            return img
        
        # Obtener el rectángulo delimitador
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Añadir padding
        padding = 10
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(gray.shape[1] - x, w + 2 * padding)
        h = min(gray.shape[0] - y, h + 2 * padding)
        
        # Recortar
        return img[y:y+h, x:x+w]
    
    def extract_with_strategy(self, img: np.ndarray, strategy: str, 
                             psm_mode: int = 6) -> List[str]:
        """
        Extrae DNIs usando una estrategia específica.
        
        Args:
            img: Imagen en formato OpenCV
            strategy: Estrategia de preprocesamiento
            psm_mode: Modo de segmentación de página de Tesseract
                - 3: Automático
                - 6: Bloque uniforme de texto
                - 11: Texto disperso
                
        Returns:
            Lista de DNIs encontrados (8 dígitos)
        """
        # Preprocesar
        processed = self.preprocess_image(img, strategy)
        
        # Corregir inclinación si es estrategia básica o de contraste
        if strategy in ['basic', 'contrast']:
            processed = self.correct_skew(processed)
        
        # OCR con configuración específica
        config = f'--psm {psm_mode} -c tessedit_char_whitelist=0123456789.'
        text = pytesseract.image_to_string(processed, config=config)
        
        # Extraer DNIs
        dnis = []
        
        # Buscar formato estándar (8 dígitos)
        dnis.extend(self.dni_pattern.findall(text))
        
        # Buscar formato con puntos/espacios
        formatted = self.dni_formatted_pattern.findall(text)
        for dni in formatted:
            # Limpiar y agregar
            clean_dni = re.sub(r'[.\s]', '', dni)
            if len(clean_dni) == 8 and clean_dni.isdigit():
                dnis.append(clean_dni)
        
        return dnis
    
    def extract_from_mrz(self, img: np.ndarray) -> Tuple[List[str], str]:
        """
        Extrae DNI específicamente de la zona MRZ (Machine Readable Zone).
        
        Args:
            img: Imagen en color del documento
            
        Returns:
            Tupla con (lista de DNIs, texto MRZ completo)
        """
        gray = self.preprocess_image(img, 'sharpen')
        
        # Configuración específica para MRZ
        config = '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<'
        mrz_text = pytesseract.image_to_string(gray, config=config)
        
        # Buscar líneas típicas de MRZ (contienen '<<')
        mrz_lines = [line for line in mrz_text.split('\n') if '<<' in line]
        
        dnis = []
        for line in mrz_lines:
            # Buscar secuencias de 8 dígitos
            dnis.extend(self.dni_pattern.findall(line))
        
        # Si no encontramos en MRZ, buscar en todo el texto
        if not dnis:
            dnis.extend(self.dni_pattern.findall(mrz_text))
        
        return dnis, mrz_text
    
    def extract_dni_multi_strategy(self, img: np.ndarray) -> Tuple[Optional[str], dict]:
        """
        Extrae DNI usando TODAS las estrategias y vota por el mejor.
        
        Este es el método principal que debes usar. Combina múltiples
        técnicas y usa votación para determinar el DNI más confiable.
        
        Args:
            img: Imagen en color del documento (BGR)
            
        Returns:
            Tupla con (DNI más confiable o None, diccionario de debug)
        """
        results = {}
        all_dnis = []
        
        # Intentar extraer solo la región del documento
        doc_region = self.extract_dni_region(img)
        
        # Estrategia 1: MRZ específico
        mrz_dnis, mrz_text = self.extract_from_mrz(doc_region)
        results['mrz'] = mrz_dnis
        all_dnis.extend(mrz_dnis)
        
        # Estrategia 2-6: Diferentes preprocesamientos con PSM 6
        strategies = ['basic', 'contrast', 'adaptive', 'denoise', 'sharpen']
        for strategy in strategies:
            dnis = self.extract_with_strategy(doc_region, strategy, psm_mode=6)
            results[f'{strategy}_psm6'] = dnis
            all_dnis.extend(dnis)
        
        # Estrategia 7-8: Mejores estrategias con PSM alternativo
        for strategy in ['contrast', 'sharpen']:
            dnis = self.extract_with_strategy(doc_region, strategy, psm_mode=11)
            results[f'{strategy}_psm11'] = dnis
            all_dnis.extend(dnis)
        
        # Votación: contar ocurrencias
        if not all_dnis:
            return None, results
        
        dni_counts = Counter(all_dnis)
        
        # El DNI más común es probablemente el correcto
        most_common_dni = dni_counts.most_common(1)[0][0]
        
        results['vote_counts'] = dict(dni_counts)
        results['winner'] = most_common_dni
        results['confidence'] = dni_counts[most_common_dni] / len(all_dnis)
        
        return most_common_dni, results

def extract_dni_from_images(img1: np.ndarray, img2: np.ndarray) -> Tuple[str, dict]:
    """
    Extrae DNI de las imágenes del frente y dorso del documento.
    
    Args:
        img1: Imagen del frente (BGR)
        img2: Imagen del dorso (BGR)
        
    Returns:
        Tupla con (DNI encontrado, información de debug)
        
    Raises:
        ValueError: Si no se encuentra ningún DNI
    """
    extractor = DNIExtractor(target_size=(1500, 1000))
    
    # Extraer de ambas imágenes
    dni1, debug1 = extractor.extract_dni_multi_strategy(img1)
    dni2, debug2 = extractor.extract_dni_multi_strategy(img2)
    
    debug_info = {
        'front': debug1,
        'back': debug2
    }
    
    # Priorizar el resultado con mayor confianza
    if dni1 and dni2:
        conf1 = debug1.get('confidence', 0)
        conf2 = debug2.get('confidence', 0)
        
        if conf1 >= conf2:
            debug_info['selected'] = 'front'
            debug_info['confidence'] = conf1
            return dni1, debug_info
        else:
            debug_info['selected'] = 'back'
            debug_info['confidence'] = conf2
            return dni2, debug_info
    
    elif dni1:
        debug_info['selected'] = 'front'
        debug_info['confidence'] = debug1.get('confidence', 0)
        return dni1, debug_info
    
    elif dni2:
        debug_info['selected'] = 'back'
        debug_info['confidence'] = debug2.get('confidence', 0)
        return dni2, debug_info
    
    raise ValueError("No se pudo extraer el DNI de ninguna imagen")


def _make_event(
    request: Request,
    *,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    actor_id: Optional[UUID] = None,
    target_id: Optional[UUID] = None,
    target_type: AuditTargetType = AuditTargetType.USER,
    details: Optional[dict] = None,
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
async def get_users(session_db: SessionDep):
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
    result: List[User] = session_db.exec(statement).scalars().all()
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
async def get_user_by_id(session_db: SessionDep, user_id: UUID):
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
    user: User = session_db.get(User, user_id)
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
            health_insurance=[i.id for i in user.health_insurance]
        ).model_dump()
    )

@private_router.get("/me", response_model=UserRead)
async def me_user(request: Request, session_db: SessionDep):
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

    user = session_db.merge(user)
    session_db.commit()
    session_db.refresh(user)

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
async def add_user(session_db: SessionDep, user: Annotated[UserCreate, Form(...)]):
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
        session_db.add(user_db)
        session_db.commit()
        session_db.refresh(user_db)
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
async def verify_dni(request: Request, dni_form: Annotated[DniForm, Form(...)], 
                     session_db: SessionDep):
    try:    
        b1 = await dni_form.front.read()
        b2 = await dni_form.back.read()
        
        def bytes_to_cv2(b):
            arr = np.frombuffer(b, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("cv2 no pudo decodificar la imagen")
            return img
        
        img1 = bytes_to_cv2(b1)
        img2 = bytes_to_cv2(b2)
        
        try:
            dni, debug_info = extract_dni_from_images(img1, img2)
            console.print(f"DNI extraído: {dni}")
            console.print(f"Confianza: {debug_info['confidence']:.2%}")
            console.print(f"Fuente: {debug_info['selected']}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Actualizar usuario
        user = session_db.get(User, request.state.user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        pre_change_dni = user.dni
        user.dni = dni
        session_db.add(user)
        session_db.commit()
        session_db.refresh(user)
        
        # Verificar cambio
        if user.dni != dni:
            session_db.rollback()
            raise HTTPException(status_code=500, 
                              detail="Error al actualizar el DNI")
        
        return {
            "dni": dni,
            "dni_anterior": pre_change_dni,
            "confidence": debug_info['confidence'],
            "source": debug_info['selected'],
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=400, 
                          detail=f"Error procesando las imágenes: {str(e)}")

@private_router.delete("/delete/{user_id}/", response_model=UserDelete)
async def delete_user(request: Request, user_id: UUID, session_db: SessionDep):
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
        user: User = session_db.get(User, user_id)

        session_db.delete(user)
        session_db.commit()
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
async def update_user(request: Request, user_id: UUID, session_db: SessionDep, user_form: Annotated[UserUpdate, Form(...)]):

    if not request.state.user.id == user_id and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not un unauthorized",
        )

    user: User = session_db.get(User, user_id)

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
                health_insurance_oj = session_db.get(HealthInsurance, health_insurance_i)
                if not health_insurance_oj in user.health_insurance:
                    user.health_insurance.append(health_insurance_oj)
            else:
                continue
        else:
            continue

    if user_form.img_profile and not "google" in request.state.scopes:
        await user.save_profile_image(user_form.img_profile)

    session_db.add(user)
    session_db.commit()
    session_db.refresh(user)

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
async def update_petition_password(
    request: Request,
    session_db: SessionDep,
    data: Annotated[UserPetitionPasswordUpdate, Form(...)],
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    try:
        user: User | None = session_db.exec(
            select(User).where(User.email == data.email)
        ).scalar_one_or_none()

        if not user:
            return ORJSONResponse({"detail": "User not found"}, status_code=404)

        code = [secrets.choice(string.ascii_letters + string.digits) for _ in range(6)]

        r_cod = "".join(code)
        
        console.print(f"User: {user} - Date Type: {type(user)}")
        
        r_code_data = {
            "user": str(user.id),
            "r_cod": r_cod,
            "state": False
        }

        rc.setex(f"recovery-codes:{user.email}", 60, dumps(r_code_data))

        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.PASSWORD_RESET_REQUESTED,
                severity=AuditSeverity.WARNING,
                actor_id=user.id,
                target_id=user.id,
                details={"email": user.email},
            )
        )

        EmailService.send_password_reset_email(user.email, reset_code=r_cod)

        return ORJSONResponse({"detail": "Ok 200"}, status_code=200)

    except Exception:
        console.print_exception(show_locals=True)
        return ORJSONResponse({"detail":"Ok 200"}, status_code=200)
    
@public_router.post("update/verify/code")
async def verify_code(session_db: SessionDep, email: str = Form(...), code: str = Form(...)):
    try:
        # Usar scalar_one_or_none para obtener un objeto User directo o None
        user = session_db.scalar(
            select(User).where(User.email == email)
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        raw = rc.get(f"recovery-codes:{user.email}")
        if not raw:
            raise HTTPException(status_code=400, detail="Invalid code")
        data = loads(raw)
        if data.get("r_cod") != code:
            raise HTTPException(status_code=400, detail="Invalid code")
        data["state"] = True
        key_name = f"recovery-codes:{user.email}"
        ttl = rc.ttl(key_name)
        ttl = ttl if ttl and ttl > 0 else 60
        rc.setex(key_name, ttl, dumps(data))
        
        return {"message": "Code verified successfully", "success": True}
    
    except HTTPException:
        # Re-lanzar HTTPExceptions (404, 400) sin modificar
        raise
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@public_router.post("/update/confirm/password", response_model=UserRead)
async def update_confirm_password(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    try:
        user: User = session.exec(
            select(User).where(User.email == email)
        ).first()[0]

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        raw = rc.get(f"recovery-codes:{user.email}")
        if not raw:
            raise HTTPException(status_code=400, detail="Invalid code")
        data = loads(raw)
        if not data.get("state"):
            raise HTTPException(status_code=401, detail="Unautorized")

        if data.get("r_cod") != code:
            raise HTTPException(status_code=400, detail="Invalid code")

        user.set_password(new_password)
        session.add(user)
        session.commit()
        session.refresh(user)

        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.PASSWORD_RESET_COMPLETED,
                actor_id=user.id,
                target_id=user.id,
                details={"email": user.email},
            )
        )

        EmailService.send_password_changed_notification_email(
            user.email,
            help_link=f"{CORS_HOST}/support",
            contact_email=EMAIL_HOST_USER,
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
async def update_user_password(
    request: Request,
    user_id: UUID,
    session: SessionDep,
    user_form: UserPasswordUpdate,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):

    if not request.state.user.id == user_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un unauthorized")

    user: User = session.get(User, user_id)
    
    console.print(f"User Form: {user}")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.check_password(user_form.old_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta",
        )

    if not user_form.confirmation_matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La confirmación de la contraseña no coincide",
        )

    user.set_password(user_form.new_password)
    session.add(user)
    session.commit()
    session.refresh(user)

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.PASSWORD_RESET_COMPLETED,
            actor_id=request.state.user.id,
            target_id=user.id,
            details={"email": user.email, "initiated_by": str(request.state.user.id)},
        )
    )

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
async def ban_user(
    request: Request,
    user_id: UUID,
    session: SessionDep,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    user: User = session_db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        record = user.deactivate(actor_id=request.state.user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.add(user)
    session.commit()
    session.refresh(user)

    await emitter.emit_record(
        record,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
    )

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
        ).model_dump(),
        "message":f"User {user.name} has been banned."
    })

@private_router.patch("/unban/{user_id}/", response_model=UserRead)
async def unban_user(
    request: Request,
    user_id: UUID,
    session: SessionDep,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    user: User = session_db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        record = user.activate(actor_id=request.state.user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.add(user)
    session.commit()
    session.refresh(user)

    await emitter.emit_record(
        record,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
    )

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
        ).model_dump(),
        "message":f"User {user.name} has been unbanned."
    })

router = APIRouter(
    tags=["users"],
    prefix="/users",
    default_response_class=ORJSONResponse,
)

router.include_router(private_router)
router.include_router(public_router)
