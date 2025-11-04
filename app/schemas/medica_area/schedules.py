from __future__ import annotations

from datetime import time as time_type
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from .enums import DayOfWeek


class MedicalScheduleBase(BaseModel):
    day: DayOfWeek
    start_time: time_type
    end_time: time_type


class MedicalScheduleCreate(MedicalScheduleBase):
    pass


class MedicalScheduleUpdate(BaseModel):
    day: Optional[DayOfWeek | str] = None
    start_time: Optional[time_type] = None
    end_time: Optional[time_type] = None

    @classmethod
    @field_validator("start_time", mode="before")
    def validate_day(cls, value: time_type):
        if value.hour < 0 or value.hour > 23:
            raise ValueError("El valor de start_time debe estar entre 0 y 23.")
        if value.minute < 0 or value.minute > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")
        if value.second < 0 or value.second > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")

        if value > cls.end_time:
            raise ValueError("El valor de start_time debe ser menor que end_time.")

        return value

    @classmethod
    @field_validator("start_time", mode="before")
    def validate_day(cls, value: time_type):
        if value.hour < 0 or value.hour > 23:
            raise ValueError("El valor de start_time debe estar entre 0 y 23.")
        if value.minute < 0 or value.minute > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")
        if value.second < 0 or value.second > 59:
            raise ValueError("El valor de start_time debe estar entre 0 y 59.")

        if value < cls.start_time:
            raise ValueError("El valor de end_time debe ser mayor que start_time.")

        return value


class MedicalScheduleResponse(MedicalScheduleBase):
    id: UUID
    doctors: Optional[List["DoctorResponse"]] = None


class MedicalScheduleDelete(BaseModel):
    id: UUID
    message: str


class Schedules(MedicalScheduleBase):
    pass


class AvailableSchedules(BaseModel):
    available_days: List[MedicalScheduleBase]
