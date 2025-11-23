from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse, Response

from app.core.auth import JWTBearer
from app.core.services.payment import PaymentService
from app.db.main import SessionDep
from app.models import Payment, PaymentMethod, Turns, User
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentStatusUpdate

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
