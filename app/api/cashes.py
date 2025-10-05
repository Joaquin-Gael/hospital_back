from fastapi import APIRouter, status, HTTPException, Request
from fastapi.params import Query, Depends
from fastapi.responses import Response, ORJSONResponse

from typing import List, Dict, Optional, Tuple

from rich.console import Console
from sqlmodel import select

from urllib.parse import urlencode

from app.schemas.cashes import CashesRead, CashesCreate, CashesUpdate
from app.core.auth import decode, JWTBearer
from app.core.interfaces.medic_area import TurnAndAppointmentRepository
from app.core.interfaces.emails import EmailService
from app.core.services.stripe_payment import StripeServices
from app.db.main import SessionDep
from app.models import Cashes

console = Console()

router = APIRouter(
    prefix="/cashes",
    tags=["cashes"]
)

auth = JWTBearer()

public_router, private_router = APIRouter(prefix=""), APIRouter(prefix="", dependencies=[Depends(auth)])

@public_router.get("/pay/success")
async def pay_success(session: SessionDep, a:str = Query(...)):
    """
    Maneja la confirmación de pago exitoso desde Stripe.
    
    Procesa la respuesta de Stripe después de un pago exitoso,
    decodifica los datos de la transacción y crea el registro
    en el sistema de cajas.
    
    Args:
        session (SessionDep): Sesión de base de datos
        a (str): Datos de pago codificados en hexadecimal desde Stripe
        
    Returns:
        Response: Redirección HTTP a panel de usuario
            - Éxito: redirige a appointments?success=true
            - Error: redirige a appointments?success=false&services=...
            
    Raises:
        HTTPException: 500 si hay errores procesando los datos
        
    Note:
        - Decodifica datos hexadecimales de Stripe
        - Crea registro detallado en sistema de cajas
        - Maneja servicios asociados al pago
        - Redirige al frontend con parámetros de estado
    """
    try:
        data = decode(
            bytes.fromhex(a)
        )

        console.print(data)
        
        success = await StripeServices.create_cash_detail(
            session,
            **data
        )
        
        services_query: List = decode(
            bytes.fromhex(data["services"])
        )

        console.print(services_query)
        
        if success:
            return Response(status_code=302, headers={"Location": "http://localhost:4200/user_panel/appointments?success=true"})
        else:
            return Response(status_code=307, headers={"Location": f"http://localhost:4200/user_panel/appointments?success=false&{urlencode({"services":data["services"]})}"})

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@public_router.get("/pay/cancel")
async def pay_cansel(b: str = Query(...)):
    """
    Maneja la cancelación de pago desde Stripe.
    
    Procesa cuando el usuario cancela el pago en Stripe,
    decodifica los datos de la transacción cancelada y
    redirige al usuario de vuelta al panel.
    
    Args:
        b (str): Datos de transacción codificados en hexadecimal
        
    Returns:
        Response: Redirección HTTP al panel de citas del usuario
        
    Raises:
        HTTPException: 500 si hay errores procesando los datos
        
    Note:
        - No requiere procesamiento especial de cancelación
        - Simplemente redirige al panel de usuario
        - Mantiene logs para debugging
    """
    try:
        data = decode(
            bytes.fromhex(b)
        )

        console.print(data)

        return Response(status_code=302, headers={"Location": "http://localhost:4200/user_panel/appointments"})

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@private_router.get("/", response_model=List[CashesRead])
async def get_cashes(request: Request, session: SessionDep):
    """
    Obtiene todos los registros de transacciones del sistema de cajas.
    
    Lista todas las transacciones financieras (ingresos y gastos) 
    registradas en el sistema. Solo accesible por administradores.
    
    Args:
        request (Request): Request con información de autenticación
        session (SessionDep): Sesión de base de datos
        
    Returns:
        ORJSONResponse: Lista de transacciones serializadas con:
            - id: ID de la transacción
            - income: Monto de ingreso
            - expense: Monto de gasto  
            - date: Fecha de la transacción
            - time_transaction: Hora de la transacción
            - balance: Balance después de la transacción
            
    Raises:
        HTTPException: 401 si no tiene scopes de administrador
        
    Note:
        - Requiere scope "admin" para acceso
        - Incluye todas las transacciones históricas
        - Útil para reportes financieros y auditorías
    """
    if "admin" not in request.state.scopes:
        raise HTTPException(
            status_code=401,
            detail="Bad Scopes"
        )

    cashes: List[Cashes] = session.exec(
        select(Cashes).where(True)
    ).fetchall()

    cashes_serialized = [
        CashesRead(
            id=cash.id,
            income=cash.income,
            expense=cash.expense,
            date=cash.date,
            time_transaction = cash.time_transaction,
            balance = cash.balance,
        ).model_dump() for cash in cashes
    ]

    return ORJSONResponse(
        cashes_serialized,
        status_code=200
    )

router.include_router(public_router)
router.include_router(private_router)