from .appointments import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentDelete,
    AppointmentResponse,
    AppointmentUpdate,
)
from .chat import ChatBase, ChatResponse, MessageBase, MessageResponse
from .departments import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentDelete,
    DepartmentResponse,
    DepartmentUpdate,
)
from .doctors import (
    DoctorAuth,
    DoctorBase,
    DoctorCreate,
    DoctorDelete,
    DoctorPasswordUpdate,
    DoctorResponse,
    DoctorSpecialityUpdate,
    DoctorUpdate,
)
from .enums import DayOfWeek, DoctorStates, TurnsState
from .health_insurance import (
    HealthInsuranceBase,
    HealthInsuranceCreate,
    HealthInsuranceDelete,
    HealthInsuranceRead,
    HealthInsuranceUpdate,
)
from .locations import (
    LocationBase,
    LocationCreate,
    LocationDelete,
    LocationResponse,
    LocationUpdate,
)
from .schedules import (
    AvailableSchedules,
    MedicalScheduleBase,
    MedicalScheduleCreate,
    MedicalScheduleDelete,
    MedicalScheduleResponse,
    MedicalScheduleUpdate,
    Schedules,
)
from .services import (
    ServiceBase,
    ServiceCreate,
    ServiceDelete,
    ServiceResponse,
    ServiceUpdate,
)
from .specialties import (
    SpecialtyBase,
    SpecialtyCreate,
    SpecialtyDelete,
    SpecialtyResponse,
    SpecialtyUpdate,
)
from .turns import (
    PayTurnResponse,
    TurnReschedule,
    TurnsBase,
    TurnsCreate,
    TurnsDelete,
    TurnsResponse,
    TurnsUpdate,
)

__all__ = [
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentDelete",
    "AppointmentResponse",
    "AppointmentUpdate",
    "AvailableSchedules",
    "ChatBase",
    "ChatResponse",
    "DayOfWeek",
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentDelete",
    "DepartmentResponse",
    "DepartmentUpdate",
    "DoctorAuth",
    "DoctorBase",
    "DoctorCreate",
    "DoctorDelete",
    "DoctorPasswordUpdate",
    "DoctorResponse",
    "DoctorSpecialityUpdate",
    "DoctorStates",
    "DoctorUpdate",
    "HealthInsuranceBase",
    "HealthInsuranceCreate",
    "HealthInsuranceDelete",
    "HealthInsuranceRead",
    "HealthInsuranceUpdate",
    "LocationBase",
    "LocationCreate",
    "LocationDelete",
    "LocationResponse",
    "LocationUpdate",
    "MedicalScheduleBase",
    "MedicalScheduleCreate",
    "MedicalScheduleDelete",
    "MedicalScheduleResponse",
    "MedicalScheduleUpdate",
    "MessageBase",
    "MessageResponse",
    "PayTurnResponse",
    "Schedules",
    "ServiceBase",
    "ServiceCreate",
    "ServiceDelete",
    "ServiceResponse",
    "ServiceUpdate",
    "SpecialtyBase",
    "SpecialtyCreate",
    "SpecialtyDelete",
    "SpecialtyResponse",
    "SpecialtyUpdate",
    "TurnReschedule",
    "TurnsBase",
    "TurnsCreate",
    "TurnsDelete",
    "TurnsResponse",
    "TurnsState",
    "TurnsUpdate",
]

LocationResponse.model_rebuild()
DepartmentResponse.model_rebuild()
SpecialtyResponse.model_rebuild()
ServiceResponse.model_rebuild()
DoctorResponse.model_rebuild()
MedicalScheduleResponse.model_rebuild()
ChatResponse.model_rebuild()
MessageResponse.model_rebuild()
TurnsResponse.model_rebuild()
AppointmentResponse.model_rebuild()
HealthInsuranceRead.model_rebuild()
