from enum import Enum


class DoctorStates(str, Enum):
    available = "available"
    busy = "busy"
    offline = "offline"


class DayOfWeek(str, Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class TurnsState(str, Enum):
    waiting = "waiting"
    finished = "finished"
    cancelled = "cancelled"
    rejected = "rejected"
    accepted = "accepted"
