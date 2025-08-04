from fastapi import APIRouter, status, HTTPException
from fastapi.params import Query
from fastapi.responses import Response, ORJSONResponse

from typing import List, Dict, Optional, Tuple

from rich.console import Console

from app.schemas.cashes import *
from app.core.auth import decode
from app.core.interfaces.medic_area import TurnAndAppointmentRepository
from app.core.interfaces.emails import EmailService

console = Console()

router = APIRouter(
    prefix="/cashes",
    tags=["cashes"]
)

@router.get("/pay/success")
async def pay_success(a:str = Query(...)):
    try:
        data = decode(
            bytes.fromhex(a)
        )

        console.print(data)

        return True

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/pay/cancel")
async def pay_success(b: str = Query(...)):
    try:
        data = decode(
            bytes.fromhex(b)
        )

        console.print(data)

        return True

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))