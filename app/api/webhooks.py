from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import ORJSONResponse

from rich.console import Console

from app.core.services.payment import PaymentService
from app.core.services.stripe_payment import StripeServices
from app.db.main import SessionDep

console = Console()

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    session: SessionDep,
):
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    try:
        event = StripeServices.construct_event(payload, signature)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    payment_service = PaymentService(session)

    try:
        payment = await StripeServices.handle_webhook_event(payment_service, event)
    except Exception:
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing Stripe webhook",
        )

    return ORJSONResponse(
        {
            "received": True,
            "event": event.get("type"),
            "payment_id": str(payment.id) if payment else None,
            "payment_status": getattr(payment, "status", None),
        }
    )
