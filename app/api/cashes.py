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