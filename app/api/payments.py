from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse, Response
from sqlmodel import select

import stripe

from app.core.auth import JWTBearer
from app.core.services.payment import PaymentService
from app.db.main import SessionDep
from app.models import Payment, PaymentMethod, PaymentStatus, Turns, User
from app.schemas.medica_area.turns import PayTurnResponse, TurnsResponse
from app.schemas.payment import (
    PaymentCreate,
    PaymentRead,
    PaymentStatusUpdate,
    PaymentTurnCreate,
)

auth = JWTBearer()

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    default_response_class=ORJSONResponse,
    dependencies=[Depends(auth)],
)


def _serialize_payment(payment: Payment) -> dict:
    return PaymentRead.model_validate(payment, from_attributes=True).model_dump()


@router.get("/", response_model=List[PaymentRead])
async def list_payments(
    request: Request,
    session: SessionDep,
    user_id: Optional[UUID] = None,
):
    user = request.state.user
    service = PaymentService(session)
    target_user_id = user_id if getattr(user, "is_superuser", False) else getattr(user, "id", None)
    payments = service.list_payments(target_user_id)
    return [_serialize_payment(payment) for payment in payments]


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    request: Request,
    session: SessionDep,
    payment_id: UUID,
):
    payment = PaymentService(session).get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    user = request.state.user
    if not getattr(user, "is_superuser", False) and payment.user_id not in (None, getattr(user, "id", None)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this payment")

    return _serialize_payment(payment)


@router.post("/add", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: Request,
    session: SessionDep,
    payload: PaymentCreate,
):
    turn = session.get(Turns, payload.turn_id)
    if turn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    user = request.state.user
    if not getattr(user, "is_superuser", False) and turn.user_id != getattr(user, "id", None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create this payment")

    patient: User | None = session.get(User, payload.user_id) if payload.user_id else session.get(User, turn.user_id)

    service = PaymentService(session)
    payment = await service.create_payment_for_turn(
        turn=turn,
        appointment=turn.appointment,
        user=patient,
        payment_method=payload.payment_method or PaymentMethod.card,
        gateway_metadata=payload.gateway_metadata,
    )

    return _serialize_payment(payment)


@router.post("/turn", response_model=PayTurnResponse, status_code=status.HTTP_201_CREATED)
async def recreate_turn_payment_session(
    request: Request,
    session: SessionDep,
    payload: PaymentTurnCreate,
):
    """
    Crea o reutiliza una sesión de pago para un turno existente.
    
    - Si existe un pago pendiente válido (< 23 horas), lo reutiliza
    - Si el pago está expirado, lo cancela y crea uno nuevo
    - Si no existe pago, crea uno nuevo
    
    Esto previene la creación de pagos duplicados.
    """
    # 1. Obtener el turno
    turn = session.get(Turns, payload.turn_id)
    if turn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    # 2. Verificar autorización
    user = request.state.user
    if not getattr(user, "is_superuser", False) and turn.user_id != getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create this payment",
        )

    # 3. ✅ Buscar si ya existe un pago pendiente para este turno
    existing_payment = session.exec(
        select(Payment)
        .where(Payment.turn_id == payload.turn_id)
        .where(Payment.status == PaymentStatus.pending)
        .order_by(Payment.created_at.desc())
    ).first()

    # 4. ✅ Si existe un pago pendiente reciente, intentar reutilizarlo
    if existing_payment:
        payment_age = datetime.utcnow() - existing_payment.created_at
        
        # Si el pago tiene menos de 23 horas, verificar si la sesión de Stripe sigue válida
        if payment_age < timedelta(hours=23) and existing_payment.gateway_session_id:
            try:
                # Verificar el estado de la sesión en Stripe
                stripe_session = stripe.checkout.Session.retrieve(existing_payment.gateway_session_id)
                
                # Si la sesión sigue abierta, reutilizarla
                if stripe_session.status == "open":
                    payment_read = PaymentRead.model_validate(existing_payment, from_attributes=True)
                    turn_response = TurnsResponse.model_validate(turn, from_attributes=True)
                    
                    return ORJSONResponse(
                        PayTurnResponse(
                            turn=turn_response,
                            payment=payment_read,
                            payment_url=existing_payment.payment_url,
                        ).model_dump(),
                        status_code=status.HTTP_200_OK  # 200 porque estamos reutilizando
                    )
                
            except stripe.error.StripeError as e:
                # Si hay error con Stripe, continuar para crear nueva sesión
                print(f"Stripe error al verificar sesión: {e}")
                pass
        
        # ✅ Si llegamos aquí, el pago está expirado o la sesión no es válida - cancelarlo
        existing_payment.status = PaymentStatus.cancelled
        existing_payment.gateway_metadata = {
            **(existing_payment.gateway_metadata or {}),
            "cancelled_reason": "expired_or_invalid_session",
            "cancelled_at": datetime.utcnow().isoformat()
        }
        session.add(existing_payment)
        session.commit()

    # 5. ✅ Crear un nuevo pago
    patient: User | None = session.get(User, turn.user_id) if turn.user_id else None

    payment = await PaymentService(session).create_payment_for_turn(
        turn=turn,
        appointment=turn.appointment,
        user=patient,
        payment_method=payload.payment_method,
        gateway_metadata={
            **(payload.gateway_metadata or {}),
            "recreated": True,
            "previous_payment_cancelled": existing_payment is not None
        },
        health_insurance_id=getattr(turn, "health_insurance", None),
    )

    payment_read = PaymentRead.model_validate(payment, from_attributes=True)
    turn_response = TurnsResponse.model_validate(turn, from_attributes=True)

    return ORJSONResponse(
        PayTurnResponse(
            turn=turn_response,
            payment=payment_read,
            payment_url=payment.payment_url,
        ).model_dump(),
        status_code=status.HTTP_201_CREATED
    )


@router.patch("/{payment_id}/status", response_model=PaymentRead)
async def update_payment_status(
    request: Request,
    session: SessionDep,
    payment_id: UUID,
    payload: PaymentStatusUpdate,
):
    service = PaymentService(session)
    payment = service.get_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    user = request.state.user
    if not getattr(user, "is_superuser", False) and payment.user_id != getattr(user, "id", None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this payment")

    try:
        updated = service.update_status(
            payment,
            payload.status,
            gateway_metadata=payload.gateway_metadata,
            payment_url=payload.payment_url,
            gateway_session_id=payload.gateway_session_id,
        )
    except ValueError as exc:  # pragma: no cover - domain validation
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _serialize_payment(updated)


@router.get("/status", response_model=PaymentRead)
async def get_payment_status_by_session(
    request: Request,
    session: SessionDep,
    session_id: str,
):
    payment = PaymentService(session).get_payment_by_session(session_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    user = request.state.user
    if not getattr(user, "is_superuser", False) and payment.user_id != getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment",
        )

    return _serialize_payment(payment)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    request: Request,
    session: SessionDep,
    payment_id: UUID,
):
    service = PaymentService(session)
    payment = service.get_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    user = request.state.user
    if not getattr(user, "is_superuser", False) and payment.user_id != getattr(user, "id", None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this payment")

    service.delete_payment(payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)