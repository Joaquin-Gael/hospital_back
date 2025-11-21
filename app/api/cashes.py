from fastapi import APIRouter, status, HTTPException, Request
from fastapi.params import Query, Depends
from fastapi.responses import Response, ORJSONResponse

from typing import List
from uuid import UUID

from rich.console import Console
from sqlmodel import select

from app.schemas.cashes import CashesRead, CashesCreate, CashesUpdate
from app.core.auth import JWTBearer
from app.db.main import SessionDep
from app.models import Cashes
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

router = APIRouter(
    prefix="/cashes",
    tags=["cashes"]
)

auth = JWTBearer()

public_router, private_router = APIRouter(prefix=""), APIRouter(prefix="", dependencies=[Depends(auth)])


def _make_event(
    request: Request,
    *,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
    details: dict | None = None,
) -> AuditEventCreate:
    return AuditEventCreate(
        action=action,
        severity=severity,
        target_type=AuditTargetType.PAYMENT,
        actor_id=actor_id,
        target_id=target_id,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
        details=dict(details or {}),
    )

@public_router.get("/pay/success")
async def pay_success(
    request: Request,
    session_id: str | None = Query(None),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """
    Callback de éxito para Stripe (uso solo para redirecciones).

    El estado del pago ahora se procesa mediante webhooks.
    Este endpoint se mantiene para no romper los flujos
    existentes del frontend y solo genera un evento de auditoría
    antes de redirigir al panel del usuario.
    """
    try:
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.PAYMENT_SUCCEEDED,
                target_id=None,
                details={
                    "note": "Stripe redirect callback deprecated; payment handled via webhook",
                    "session_id": session_id,
                },
            )
        )
        return Response(
            status_code=302,
            headers={"Location": "http://localhost:4200/user_panel/appointments?success=true"},
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@public_router.get("/pay/cancel")
async def pay_cansel(
    request: Request,
    session_id: str | None = Query(None),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """
    Callback de cancelación para Stripe (solo redirección).

    El estado del pago ahora se determina con el webhook
    `/webhooks/stripe`. Este endpoint permanece como respaldo
    para redireccionar y auditar la acción del usuario.
    """
    try:
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.PAYMENT_CANCELLED,
                severity=AuditSeverity.WARNING,
                target_id=None,
                details={
                    "reason": "user_cancelled_redirect",
                    "session_id": session_id,
                },
            )
        )
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