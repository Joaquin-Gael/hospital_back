from pydoc import doc
from typing import Tuple

import random
from sqlalchemy.exc import IntegrityError
from sqlalchemy import extract, func
from sqlmodel import Session, select

from datetime import datetime, timedelta, date as date_type, time as time_type

import polars as pl

from uuid import UUID

from app.core.utils import BaseInterface
from app.core.interfaces.oauth import console
from app.schemas.medica_area import TurnsCreate, DoctorStates
from app.models import (
    Turns,
    Appointments,
    MedicalSchedules,
    Services,
    Doctors,
    User,
    DayOfWeek,
    Specialties,
    TurnsSchedulesLink,
)

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
    async def count_available_doctors_for_specialty(
        session: Session, specialty_id: UUID
    ) -> tuple[int, bool]:
        specialty = session.get(Specialties, specialty_id)

        if specialty is None:
            return 0, False

        available_doctors = 0

        for doctor in specialty.doctors:
            schedules = session.exec(
                select(MedicalSchedules)
                .join(MedicalSchedules.doctors)
                .where(
                    Doctors.id == doctor.id,
                    MedicalSchedules.available == True,
                )
            ).all()

            for schedule in schedules:
                if schedule.max_patients is None:
                    available_doctors += 1
                    break

                if len(schedule.turns) < schedule.max_patients:
                    available_doctors += 1
                    break

        return available_doctors, available_doctors > 0
    
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
            appointment = turn.appointment

            session.delete(turn)
            session.flush()

            session.delete(appointment)
            
            # ✅ Commit al final
            session.commit()

            session.refresh(turn)
            session.refresh(appointment)

            return True
        except IntegrityError as e:
            session.rollback()
            return False

    @staticmethod
    async def create_turn_and_appointment(
        session: Session,
        turn: TurnsCreate,
        doctor: Doctors | None = None,
    ) -> Tuple[Turns, Appointments] | Tuple[None, str]:
        try:
            console.print(f"Serial Turn: {turn}")

            # ✅ NO usar session.begin() - la transacción ya está activa por el dependency de FastAPI
            services = []
            for service_id in turn.services:
                service = session.get(Services, service_id)
                if not service:
                    return None, f"Service with ID {service_id} not found"
                services.append(service)

            speciality = services[0].speciality

            if doctor is None and turn.doctor_id:
                doctor = session.get(Doctors, turn.doctor_id)

            if doctor:
                if doctor.speciality_id != speciality.id:
                    return None, "Selected doctor is not linked to the service speciality"
            else:
                if not speciality.doctors:
                    return None, "No doctors available for the selected speciality"
                doctor = random.choice(speciality.doctors)
            
            console.print(f"Doctor: {doctor}")

            day_map = {
                0: DayOfWeek.monday,
                1: DayOfWeek.tuesday,
                2: DayOfWeek.wednesday,
                3: DayOfWeek.thursday,
                4: DayOfWeek.friday,
                5: DayOfWeek.saturday,
                6: DayOfWeek.sunday,
            }

            requested_day = day_map.get(turn.date.weekday())

            schedules = session.exec(
                select(MedicalSchedules)
                .join(MedicalSchedules.doctors)
                .where(
                    Doctors.id == doctor.id,
                    MedicalSchedules.day == requested_day,
                    MedicalSchedules.start_time <= turn.time,
                    MedicalSchedules.end_time >= turn.time,
                )
            ).all()

            matching_schedule = schedules[0] if schedules else None

            if matching_schedule is None:
                return None, "No matching schedule found for the selected date"

            turns_on_date = session.exec(
                select(func.count(Turns.id))
                .join(TurnsSchedulesLink, TurnsSchedulesLink.turn_id == Turns.id)
                .where(
                    TurnsSchedulesLink.medical_schedule_id == matching_schedule.id,
                    Turns.date == turn.date,
                )
            ).one()

            if matching_schedule.max_patients is not None:
                if turns_on_date >= matching_schedule.max_patients:
                    return None, "No available slots in the schedule"

            if matching_schedule.available is False and matching_schedule.max_patients is None:
                return None, "No available slots in the schedule"

            new_turn = Turns(
                reason=turn.reason,
                state=turn.state,
                date=turn.date,
                date_limit=turn.date + timedelta(days=1),
                user_id=turn.user_id,
                doctor_id=doctor.id,
                services=services,
                time=turn.time,
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

            matching_schedule.turns.append(new_turn)
            session.add(matching_schedule)
            session.flush()

            session.refresh(matching_schedule)

            latest_turns_on_date = session.exec(
                select(func.count(Turns.id))
                .join(TurnsSchedulesLink, TurnsSchedulesLink.turn_id == Turns.id)
                .where(
                    TurnsSchedulesLink.medical_schedule_id == matching_schedule.id,
                    Turns.date == turn.date,
                )
            ).one()

            if matching_schedule.max_patients is not None:
                matching_schedule.available = latest_turns_on_date < matching_schedule.max_patients
                if latest_turns_on_date > matching_schedule.max_patients:
                    session.rollback()
                    return None, "No available slots in the schedule"

            # ✅ Commit al final
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

    @staticmethod
    async def reschedule_turn(
        session: Session,
        turn: Turns,
        *,
        date: date_type,
        time: time_type,
    ) -> Turns:
        if turn is None:
            raise ValueError("Turn not found")

        if not turn.services:
            raise ValueError("Turn has no associated services")

        # Obtener la especialidad del turno desde los servicios
        specialty = turn.services[0].speciality
        
        if not specialty:
            raise ValueError("Service has no associated specialty")

        day_map = {
            1: DayOfWeek.monday,
            2: DayOfWeek.tuesday,
            3: DayOfWeek.wednesday,
            4: DayOfWeek.thursday,
            5: DayOfWeek.friday,
            6: DayOfWeek.saturday,
            7: DayOfWeek.sunday,
        }

        target_day = day_map.get(date.isoweekday())

        if target_day is None:
            raise ValueError("Invalid date for scheduling")

        session.refresh(turn)

        # CAMBIO CRÍTICO: Buscar schedules de CUALQUIER doctor de la especialidad
        # Primero intentar con el doctor actual
        schedule = session.exec(
            select(MedicalSchedules)
            .join(MedicalSchedules.doctors)
            .where(
                Doctors.id == turn.doctor_id,
                MedicalSchedules.day == target_day,
            )
            .limit(1)
        ).first()

        assigned_doctor_id = turn.doctor_id
        
        # Si el doctor actual no tiene horario ese día, buscar otro doctor de la especialidad
        if schedule is None:
            console.print(f"⚠️ Doctor {turn.doctor_id} no disponible para {target_day}, buscando alternativa...")
            
            # Obtener todos los schedules de la especialidad para ese día
            available_schedules = session.exec(
                select(MedicalSchedules)
                .join(MedicalSchedules.doctors)
                .join(Doctors.speciality)
                .where(
                    Specialties.id == specialty.id,
                    MedicalSchedules.day == target_day,
                    MedicalSchedules.available == True,
                )
            ).all()
            
            if not available_schedules:
                raise ValueError("No matching schedule found for the selected date")
            
            # Buscar el schedule con más capacidad disponible
            best_schedule = None
            for sched in available_schedules:
                if sched.max_patients is None:
                    best_schedule = sched
                    break
                
                available_slots = sched.max_patients - len(sched.turns)
                if available_slots > 0:
                    if best_schedule is None:
                        best_schedule = sched
                    else:
                        current_best_slots = (best_schedule.max_patients or 0) - len(best_schedule.turns)
                        if available_slots > current_best_slots:
                            best_schedule = sched
            
            if best_schedule is None:
                raise ValueError("No available slots in the schedule")
            
            schedule = best_schedule
            # Cambiar al nuevo doctor
            assigned_doctor_id = schedule.doctors[0].id if schedule.doctors else turn.doctor_id
            console.print(f"✅ Turno reasignado a doctor {assigned_doctor_id}")

        # Validar que hay espacio disponible
        turn_is_already_assigned = schedule in turn.schedules
        scheduled_patients = len(schedule.turns) - (1 if turn_is_already_assigned else 0)

        if schedule.max_patients is not None and scheduled_patients >= schedule.max_patients:
            raise ValueError("No available slots in the schedule")

        try:
            # Remover turno de schedules anteriores
            previous_schedules = list(turn.schedules)

            for previous_schedule in previous_schedules:
                if turn in previous_schedule.turns:
                    previous_schedule.turns.remove(turn)

                if (
                    previous_schedule.max_patients is None
                    or len(previous_schedule.turns) < previous_schedule.max_patients
                ):
                    previous_schedule.available = True

                session.add(previous_schedule)

            turn.schedules.clear()
            session.flush()

            # Actualizar el turno con nueva fecha, hora y posiblemente nuevo doctor
            turn.date = date
            turn.date_limit = date + timedelta(days=1)
            turn.time = time
            turn.doctor_id = assigned_doctor_id  # Puede cambiar de doctor

            # Agregar turno al nuevo schedule
            schedule.turns.append(turn)

            if schedule.max_patients is not None:
                schedule.available = len(schedule.turns) < schedule.max_patients
            else:
                schedule.available = True

            if turn.appointment and turn.appointment.doctor_id != assigned_doctor_id:
                turn.appointment.doctor_id = assigned_doctor_id
                session.add(turn.appointment)

            session.add(schedule)
            session.add(turn)
            
            session.commit()

        except Exception as exc:
            console.print_exception(show_locals=True)
            session.rollback()
            raise

        session.refresh(turn)
        session.refresh(schedule)

        return turn