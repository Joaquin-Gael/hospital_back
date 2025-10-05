from pydoc import doc
from typing import Tuple

import random
from sqlalchemy.exc import IntegrityError
from sqlalchemy import extract
from sqlmodel import Session, select

from datetime import datetime, timedelta

import polars as pl

from uuid import UUID

from app.core.utils import BaseInterface
from app.core.interfaces.oauth import console
from app.schemas.medica_area import TurnsCreate, DoctorStates
from app.models import Turns, Appointments, MedicalSchedules, Services, Doctors, User

class DoctorRepository(BaseInterface):
    @staticmethod
    async def get_doctors(session: Session) -> list[Doctors]:
        return session.exec(select(Doctors)).all()
    
    @staticmethod
    async def get_doctor_by_id(session: Session, doctor_id: UUID) -> Doctors:
        return session.exec(select(Doctors).where(Doctors.id == doctor_id)).first()
    
    @staticmethod
    async def get_available_doctors(session: Session) -> list[Doctors]:
        return session.exec(select(Doctors).where(Doctors.doctor_state == DoctorStates.available.value)).all()
    
    @staticmethod
    async def get_doctor_metrics(session: Session, doctor: Doctors) -> pl.DataFrame:
        
        turns = session.exec(
            select(Turns).where(
                Turns.doctor_id == doctor.id,
                extract('year', Turns.date).in_([datetime.now().year, datetime.now().year-1])
            )
        ).all()
        
        if len(turns) == 0:
            return {"detail":"No Data Found"}
        
        df = pl.DataFrame(
            {
                "date": [turn.date for turn in turns],
                "day": [turn.date.day for turn in turns],
                "month": [turn.date.month for turn in turns],
                "year": [turn.date.year for turn in turns],
                "time": [turn.time for turn in turns],
                "reason": [turn.reason for turn in turns],
                "state": [turn.state for turn in turns],
            }
        )
        
        df = df.with_columns(
            pl.col("date").dt.strftime("%Y-%m-%d"),
            pl.col("time").dt.strftime("%H:%M:%S"),
        )
        
        df_finished = df.filter(
            pl.col("state") == "finished"
        )
        
        if len(df_finished) == 0:
            return {"detail":"No Data Found"}
        
        df_turns_per_month = df_finished.filter(
            pl.col("month").is_in([datetime.now().month, datetime.now().month-1]),
        )
        
        df_all_turns_in_this_month = df.filter(
            pl.col("month") == datetime.now().date().month
        ).group_by(["state", "day"]).agg(
            pl.col("state").count().alias("total_turns"),
        )
        
        df_this_month = df_finished.filter(
            pl.col("month") == datetime.now().month,
        )
        
        df_this_month = df_this_month.group_by("day").agg(
            pl.col("date").count().alias("turns_per_day")
        )
        
        df_turns_per_month = df_turns_per_month.group_by("month").agg(
            pl.col("date").count().alias("turns_per_month")
        )
        
        df_turns_per_month = df_turns_per_month.sort("month").with_columns(
            pl.col("month").pct_change().alias("monthly_growth")
        )
        
        console.print(df_all_turns_in_this_month)
        
        serial = {
            "turns_per_month":{
                "card":{},
                "line_chart":{},
                "pipe_chart": {}
            }
        }
        
        for k, v in df_turns_per_month.to_dict().items():
            if type(v) == pl.Series:
                serial["turns_per_month"]["card"][k] = v[0]
                
        for k, v in df_this_month.to_dict().items():
            if type(v) == pl.Series:
                serial["turns_per_month"]["line_chart"][k] = [v_i for v_i in v]
                
        for k, v in df_all_turns_in_this_month.to_dict().items():
            if type(v) == pl.Series:
                serial["turns_per_month"]["pipe_chart"][k] = [v_i for v_i in v]
                
        console.print(serial)
        
        return serial
    
class TurnAndAppointmentRepository(BaseInterface):
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
                    select(MedicalSchedules)
                    .join(
                        MedicalSchedules.doctors
                    ).where(
                        Doctors.id == doctor.id
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
                        session.flush()
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