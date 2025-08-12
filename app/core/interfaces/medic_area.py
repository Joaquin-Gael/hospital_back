from typing import Tuple

from click import secho
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.schemas.medica_area import TurnsCreate
from app.models import Turns, Appointments, MedicalSchedules


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
    async def create_turn_and_appointment(session: Session, turn: TurnsCreate) -> Tuple[Turns, Appointments] | Tuple[None, str]:
        try:
            import locale

            with session.begin():
                new_turn = Turns(
                    reason=turn.reason,
                    state=turn.state,
                    date=turn.date,
                    date_limit=turn.date_limit,
                    user_id=turn.user_id,
                    doctor_id=turn.doctor_id,
                    appointment_id=turn.appointment_id,
                    services=turn.services,
                    time=turn.time
                )
                session.add(new_turn)
                session.flush()

                new_appointment = Appointments(
                    user_id=new_turn.id,
                    doctor_id=new_turn.doctor_id,
                    turn_id=new_turn.id,
                )

                schedules = session.exec(
                    select(MedicalSchedules).where(
                        turn.doctor_id in MedicalSchedules.doctors
                    )
                ).fetchall()

                locale.setlocale(locale.LC_TIME, "en_US.UTF-8")

                for schedule in schedules:
                    if schedule.day.value == turn.date.strftime("%A").lower():
                        if schedule.max_patients > len(schedule.turns):
                            schedule.turns.append(new_turn)
                        elif schedule.max_patients == len(schedule.turns):
                            schedule.turns.append(new_turn)
                            schedule.available = False
                        else:
                            raise IntegrityError

                session.add(schedule)

                session.add(new_appointment)

            session.refresh(new_turn)
            session.refresh(new_appointment)

            return new_turn, new_appointment
        except IntegrityError as e:
            session.rollback()
            return None, str(e)