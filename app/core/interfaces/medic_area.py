from typing import Tuple

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.schemas.medica_area import TurnsCreate
from app.models import Turns, Appointments


class TurnAndAppointmentRepository:
    @staticmethod
    async def delete_turn_and_appointment(session: Session, turn: Turns) -> bool:
        try:
            with session.begin():
                appointment = turn.appointment

                session.delete(turn)
                session.flush()

                session.delete(appointment)

            session.refresh(turn)
            session.refresh(appointment)

            return True
        except IntegrityError as e:
            session.rollback()
            return False

    @staticmethod
    async def create_turn_and_appointment(session: Session, turn: TurnsCreate) -> Tuple[Turns, Appointments] | None:
        try:
            with session.begin():
                new_turn = Turns(
                    reason=turn.reason,
                    state=turn.state,
                    date=turn.date,
                    date_limit=turn.date_limit,
                    user_id=turn.user_id,
                    doctor_id=turn.doctor_id,
                    appointment_id=turn.appointment_id,
                    services=turn.services
                )
                session.add(new_turn)
                session.flush()

                new_appointment = Appointments(
                    user_id=new_turn.id,
                    doctor_id=new_turn.doctor_id,
                    turn_id=new_turn.id,
                )

                session.add(new_appointment)

            session.refresh(new_turn)
            session.refresh(new_appointment)

            return new_turn, new_appointment
        except IntegrityError as e:
            session.rollback()
            return None