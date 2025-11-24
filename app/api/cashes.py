from fastapi import APIRouter, status, HTTPException, Request
from fastapi.params import Query, Depends
from fastapi.responses import Response, ORJSONResponse
from app.models import PaymentStatus
from app.core.services.payment import PaymentService

from typing import List
from uuid import UUID

from rich.console import Console
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.schemas.cashes import CashesRead, CashesCreate, CashesUpdate
from app.core.auth import JWTBearer
from app.db.main import SessionDep
from app.models import Cashes
from app.config import FRONTEND_URL  # ✅ Importar
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
import stripe

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
    session: SessionDep,
    session_id: str | None = Query(None),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """
    Callback de éxito para Stripe.
    
    Actualiza el estado del pago como fallback si el webhook no se procesó.
    """
    try:
        # Buscar el pago por session_id
        if session_id:
            payment_service = PaymentService(session)
            payment = payment_service.get_payment_by_session(session_id)
            
            if payment:
                # Verificar con Stripe el estado real
                stripe_session = stripe.checkout.Session.retrieve(session_id)
                
                # Actualizar solo si el pago fue exitoso en Stripe
                if stripe_session.payment_status == "paid" and payment.status == PaymentStatus.pending:
                    payment_service.update_status(
                        payment,
                        PaymentStatus.succeeded,
                        gateway_metadata={
                            **(payment.gateway_metadata or {}),
                            "updated_via": "success_callback",
                            "stripe_payment_status": stripe_session.payment_status,
                        }
                    )
                    
                    await emitter.emit_event(
                        _make_event(
                            request,
                            action=AuditAction.PAYMENT_SUCCEEDED,
                            target_id=payment.id,
                            details={
                                "session_id": session_id,
                                "payment_id": str(payment.id),
                                "updated_via": "callback_fallback",
                            },
                        )
                    )
        
        # ✅ Usar variable de entorno
        return Response(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/user_panel/appointments?success=true"},
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@public_router.get("/pay/cancel")
async def pay_cancel(
    request: Request,
    session_id: str | None = Query(None),
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """
    Callback de cancelación para Stripe (solo redirección).
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
        
        # ✅ Usar variable de entorno
        return Response(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/user_panel/appointments"}
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@private_router.get("/", response_model=List[CashesRead])
async def get_cashes(request: Request, session: SessionDep):
    """Obtiene todos los registros de transacciones del sistema de cajas."""
    if "admin" not in request.state.scopes:
        raise HTTPException(
            status_code=401,
            detail="Bad Scopes"
        )

    cashes: List[Cashes] = session.exec(
        select(Cashes).options(selectinload(Cashes.details))
    ).all()

    return ORJSONResponse(
        [CashesRead.model_validate(cash).model_dump() for cash in cashes],
        status_code=200
    )

router.include_router(public_router)
router.include_router(private_router)