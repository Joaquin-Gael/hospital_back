import stripe
import stripe as st

from datetime import datetime

from urllib.parse import urlencode

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from rich.console import Console

from app.models import Cashes, CashDetails, Turns, HealthInsurance
from app.config import stripe_secret_key, stripe_public_key, cors_host, id_prefix
from app.core.auth import encode

console = Console()

stripe.api_key = stripe_secret_key

class StripeServices:
    @staticmethod
    async def proces_payment(price: float, details: dict, h_i: UUID, session: Session) -> str | None:
        line_items:list = []

        health_insurance = session.get(HealthInsurance, h_i)

        for detail in details["products_data"]:
            line_items.append({
                "price_data": {
                    "currency": "USD",
                    "unit_amount": int(round(detail["price"]*100)*(1-(health_insurance.discount/100))),
                    "product_data": {
                        "name": detail["name"],
                        "description": detail["description"],
                    },
                },
                "quantity": detail["quantity"],
            })

        try:
            payload = {
                "a":encode(
                    {
                        "turn_id": str(details["turn_id"]),
                        "total":price*float(1-(health_insurance.discount/100)),
                        "payment_method": "card",
                        "discount":health_insurance.discount,
                        "services":encode(details["products_data"]).hex()
                    }
                ).hex()
            }

            bad_payload = {
                "b": encode(
                    {
                        "turn_id": str(details["turn_id"])
                    }
                ).hex()
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
    async def create_cash_detail(session: Session, turn_id: UUID, payment_method: str, discount: int, total: float, services: list) -> bool:
        try:
            with session.begin():
                turn = session.exec(
                    select(Turns).where(Turns.id == turn_id)
                ).first()

                open_cash = session.exec(
                    select(Cashes).where(
                        Cashes.date == datetime.now().date()
                    )
                ).first()

                if not open_cash:
                    open_cash = Cashes(
                        date=datetime.now().date()
                    )
                    session.add(open_cash)
                    session.flush()
                else:
                    session.merge(open_cash)
                    session.refresh(open_cash)

                session.refresh(turn)

                for service in turn.services:
                    open_cash.details.append(
                        CashDetails(
                            cash_id=open_cash.id,
                            service_id=service.id,
                            description=f"{service.name}-{payment_method}-{service.speciality}",
                            amount=service.price*float(1-(discount/100)),
                            total=service.price,
                            date=datetime.now().date(),
                            appointment_id=turn.appointment.id,
                            discount=discount,
                        )
                    )

                open_cash.income += total*float(1-(discount/100))
                open_cash.make_balance()

                session.add(open_cash)
                session.commit()
                
                return True
        except IntegrityError as e:
            console.print_exception(show_locals=True)
            session.rollback()
            
            return False