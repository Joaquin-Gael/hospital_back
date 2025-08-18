from typing import Tuple

import random
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from datetime import datetime, timedelta

from app.core.interfaces.oauth import console
from app.schemas.medica_area import TurnsCreate
from app.models import Turns, Appointments, MedicalSchedules, Services, Doctors, User


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
    async def create_turn_and_appointment(session: Session, turn: TurnsCreate) -> Tuple[Turns, Appointments] | Tuple[
        None, str]:
        try:
            import locale

            console.print(f"Serial Turn: {turn}")

            with session.begin():
                services = []
                for service_id in turn.services:
                    service = session.get(Services, service_id)
                    if not service:
                        return None, f"Service with ID {service_id} not found"
                    services.append(service)

                speciality = services[0].speciality

                if not speciality.doctors:
                    return None, "No doctors available for the selected speciality"
                doctor = random.choice(speciality.doctors)
                
                console.print(f"Doctor: {doctor}")


                new_turn = Turns(
                    reason=turn.reason,
                    state=turn.state,
                    date=turn.date,
                    date_limit=turn.date + timedelta(days=1),
                    user_id=turn.user_id,
                    doctor_id=doctor.id,
                    services=services,
                    time=turn.time
                )
                
                console.print(f"Turn: {new_turn}")
                session.add(new_turn)
                session.flush()

                new_appointment = Appointments(
                    user_id=new_turn.user_id,
                    doctor_id=doctor.id,
                    turn_id=new_turn.id,
                )
                console.print(f"Appointment: {new_appointment}")
                session.add(new_appointment)
                session.flush()
                
                console.print("Despues del flush")

                schedules = session.exec(
                    select(MedicalSchedules).where(
                        MedicalSchedules.doctor_id == doctor.id
                    )
                ).all()

                locale.setlocale(locale.LC_TIME, "en_US.UTF-8")

                for schedule in schedules:
                    if schedule.day.value.lower() == turn.date.strftime("%A").lower():
                        if schedule.max_patients > len(schedule.turns):
                            schedule.turns.append(new_turn)
                        elif schedule.max_patients == len(schedule.turns):
                            schedule.turns.append(new_turn)
                            schedule.available = False
                        else:
                            return None, "No available slots in the schedule"
                        session.add(schedule)
                        break

                if not schedules:
                    return None, "No matching schedule found for the selected date"
                
                session.commit()

            session.refresh(new_turn)
            session.refresh(new_appointment)

            return new_turn, new_appointment
        except IntegrityError as e:
            console.print_exception(show_locals=True)
            session.rollback()
            return None, f"Database integrity error: {str(e)}"
        except Exception as e:
            console.print_exception(show_locals=True)
            session.rollback()
            return None, f"Unexpected error: {str(e)}"