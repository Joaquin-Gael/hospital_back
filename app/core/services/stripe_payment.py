import stripe as st

from pydantic import BaseModel
from typing import Dict

from fastapi.responses import Response

from datetime import datetime

from urllib.parse import urlencode

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from rich.console import Console

from app.models import Cashes, CashesDetails, Turns
from app.config import stripe_secret_key, stripe_public_key, cors_host, id_prefix
from app.core.auth import encode

console = Console()

class StripeServices:
    @staticmethod
    async def proces_payment(price: float, details: dict) -> str | None:
        line_items:list = []

        for detail in details["products_data"]:
            line_items.append({
                "price_data": {
                    "currency": "USD",
                    "unit_amount": int(round(detail["price"]*100)),
                    "product_data": {
                        "name": detail["name"],
                        "description": detail["description"],
                    },
                },
                "quantity": detail["quantity"],
            })

        try:
            payload = {
                "a":encode({"turn_id": details["turn_id"], "total":price, "payment_method": "card"}).hex()
            }

            bad_payload = {
                "b": encode({"turn_id": details["turn_id"]}).hex()
            }

            session = st.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=f"{cors_host}/{id_prefix}/cashes/pay/success?session_id={{CHECKOUT_SESSION_ID}}&{urlencode(payload)}",
                cancel_url=f"{cors_host}/{id_prefix}/cashes/pay/cancel?{urlencode(bad_payload)}",
            )

            return session.url
        except Exception as e:
            console.print_exception(show_locals=True)
            return None

    @staticmethod
    async def create_cash_detail(session: Session, turn_id: UUID, payment_method: str):
        try:
            with session.begin():
                turn = session.exec(
                    select(Turns).where(Turns.id == turn_id)
                ).first()

                open_cash = Cashes(
                    date=datetime.now().date()
                )
                session.add(open_cash)
                session.flush()
                session.refresh(turn)

                for service in turn.services:
                    open_cash.details.append(
                        CashesDetails(
                            cash_id=open_cash.id,
                            service_id=service.id,
                            desciption=f"{service.name}-{payment_method}-{service.speciality}",
                            amount=service.price
                        )
                    )

                open_cash.income += turn.price_total()
                open_cash.make_balance()

                session.add(open_cash)
                session.commit()
        except IntegrityError as e:
            session.rollback()