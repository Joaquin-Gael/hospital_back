from fastapi import (
    APIRouter,
    Request,
    Query,
    status,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    Form,
    Response
)
from fastapi.responses import ORJSONResponse

from sqlmodel import select
from sqlalchemy.orm import selectinload

from typing import List, Optional, Dict, Annotated, TypeVar, Tuple

from rich import print
from rich.console import Console
import polars.exceptions as ple

from uuid import UUID

from app.models import (
    Doctors,
    MedicalSchedules,
    Locations,
    Services,
    Specialties,
    Departments,
    ChatMessages,
    Chat,
    User,
    Turns,
    Appointments,
    DoctorMedicalScheduleLink,
    HealthInsurance,
    Payment,
    PaymentMethod,
    UserHealthInsuranceLink
)
from app.schemas import UserRead
from app.schemas.payment import PaymentRead
from app.schemas.medica_area import (
    MedicalScheduleCreate,
    MedicalScheduleDelete,
    MedicalScheduleUpdate,
    MedicalScheduleResponse,
    AvailableSchedules,
    Schedules, PayTurnResponse
)
from app.schemas.medica_area import (
    DayOfWeek,
    TurnsState,
    DoctorStates
)
from app.schemas.medica_area import (
    DoctorResponse,
    DoctorCreate,
    DoctorDelete,
    DoctorUpdate,
    DoctorPasswordUpdate,
    DoctorSpecialityUpdate
)
from app.schemas.medica_area import (
    LocationResponse,
    LocationCreate,
    LocationDelete,
    LocationUpdate
)
from app.schemas.medica_area import (
    DepartmentResponse,
    DepartmentCreate,
    DepartmentDelete,
    DepartmentUpdate
)
from app.schemas.medica_area import (
    SpecialtyResponse,
    SpecialtyDelete,
    SpecialtyCreate,
    SpecialtyUpdate
)
from app.schemas.medica_area import (
    ServiceResponse,
    ServiceCreate,
    ServiceDelete,
    ServiceUpdate
)
from app.schemas.medica_area import (
    ChatResponse
)
from app.schemas.medica_area import (
    MessageResponse,
)
from app.schemas.medica_area import (
    TurnsResponse,
    TurnsDelete,
    TurnsUpdate,
    TurnsCreate
)
from app.schemas.medica_area import (
    AppointmentResponse,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentDelete
)
from app.schemas.medica_area import (
    HealthInsuranceRead,
    HealthInsuranceUpdate,
    HealthInsuranceDelete,
    HealthInsuranceCreate
)
from app.db.main import SessionDep
from app.core.auth import JWTBearer, JWTWebSocket, time_out
from app.core.interfaces.medic_area import TurnAndAppointmentRepository, DoctorRepository
from app.core.services.payment import PaymentService

auth = JWTBearer()
ws_auth = JWTWebSocket()

console = Console()


def require_doctor_or_admin(request: Request) -> User | Doctors:
    user = getattr(request.state, "user", None)

    if isinstance(user, Doctors):
        return user

    if isinstance(user, User) and (user.is_admin or user.is_superuser):
        return user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


departments = APIRouter(
    prefix="/departments",
    tags=["departments"],
    default_response_class=ORJSONResponse,
    dependencies=[
        Depends(auth)
    ]
)

@departments.get("/", response_model=DepartmentResponse)
async def get_departments(request: Request, session_db: SessionDep):
    result = session_db.exec(
        select(Departments)
    ).all()

    departments_list: List[DepartmentResponse] = []
    for department in result:
        specialities_list = []
        for speciality in department.specialities:
            specialities_list.append(
                SpecialtyResponse(
                    id=speciality.id,
                    name=speciality.name,
                    description=speciality.description,
                    department_id=department.id
                )
            )

        departments_list.append(
            DepartmentResponse(
                id=department.id,
                name=department.name,
                description=department.description,
                location_id=department.location_id,
                specialities=specialities_list
            ).model_dump()
        )

    return ORJSONResponse(departments_list)

@departments.get("/{department_id}/", response_model=DepartmentResponse)
async def get_department_by_id(request: Request, department_id: UUID, session_db: SessionDep):
    department = session_db.exec(
        select(Departments).where(Departments.id == department_id)
    ).first()

    specialities_list = []
    for speciality in department.specialities:
        specialities_list.append(
            SpecialtyResponse(
                id=speciality.id,
                name=speciality.name,
                description=speciality.description,
                department_id=department.id
            )
        )

    return DepartmentResponse(
        id=department.id,
        name=department.name,
        description=department.description,
        location_id=department.location_id,
        specialities=specialities_list
    ).model_dump()

@departments.post("/add/", response_model=DepartmentResponse)
async def add_department(request: Request, department: DepartmentCreate, session_db: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    new_department: Departments = Departments(
        name=department.name,
        description=department.description,
        location_id=department.location_id
    )

    session_db.add(new_department)
    session_db.commit()
    session_db.refresh(new_department)

    return DepartmentResponse(
        id=new_department.id,
        name=new_department.name,
        description=new_department.description,
        location_id=new_department.location_id
    ).model_dump()

@departments.delete("/delete/{department_id}/", response_model=DepartmentDelete)
async def delete_department_by_id(request: Request, department_id: UUID, session_db: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        department: Departments = session_db.exec(
            select(Departments).where(Departments.id == department_id)
        ).first()

        session_db.delete(department)
        session_db.commit()

        return DepartmentDelete(
            id=department.id,
            message=f"Department {department.name} has been deleted"
        ).model_dump()

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department {department_id} not found")

@departments.delete("/delete/{department_id}/specialities/{speciality_id}/", response_model=SpecialtyDelete)
async def delete_speciality_by_id(request: Request, department_id: UUID, speciality_id: UUID, session_db: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        result = session_db.execute(select(Departments).where(Departments.id == department_id)).scalars().first()
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department {department_id} not found")
        for speciality in result.specialities:
            if speciality.id == speciality_id:
                session_db.delete(speciality)
                session_db.commit()
                return SpecialtyDelete(
                    id=speciality.id,
                    message=f"Speciality {speciality.name} has been deleted"
                )
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Speciality {speciality_id} not found")
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department {department_id} don´"
                                                                           f"t has speciality {speciality_id}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Speciality {speciality_id} not found")


@departments.patch("/update/{department_id}/", response_model=DepartmentResponse)
async def update_department(request: Request, department_id: UUID , department: DepartmentUpdate, session_db: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    new_department: Departments = session_db.exec(
        select(Departments).where(Departments.id == department_id)
    ).first()

    new_department.name = department.name
    new_department.description = department.description
    new_department.location_id = department.location_id

    session_db.add(new_department)
    session_db.commit()
    session_db.refresh(new_department)

    return DepartmentResponse(
        id=new_department.id,
        name=new_department.name,
        description=new_department.description,
        location_id=new_department.location_id
    ).model_dump()

schedules = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    default_response_class=ORJSONResponse,
    dependencies=[
        Depends(auth)
    ]
)

@schedules.get("/", response_model=List[MedicalScheduleResponse])
async def get_medical_schedules(request: Request, session_db: SessionDep):
    statement = select(MedicalSchedules)
    result: List[MedicalSchedules] = session_db.exec(statement).all()
    schedules = []
    for schedule_i in result:
        doctors: List[DoctorResponse] = []
        for doc in schedule_i.doctors:
            doctor = DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id,
                address=doc.address,
                blood_type=doc.blood_type,
            )
            doctors.append(doctor)
        schedule = MedicalScheduleResponse(
            id=schedule_i.id,
            day=schedule_i.day,
            start_time=schedule_i.start_time,
            end_time=schedule_i.end_time,
            doctors=doctors
        )
        schedules.append(schedule.model_dump())

    return ORJSONResponse(
        schedules
    )

@schedules.get("/{schedule_id}", response_model=MedicalScheduleResponse)
async def get_schedule_by_id(session_db: SessionDep, schedule_id: UUID):
    try:
        schedule = session_db.get(MedicalSchedules, schedule_id)
        doctors_by_schedule_serialized: List[DoctorResponse] = [
            DoctorResponse(
                username=doc.name,
                dni=doc.dni,
                id=doc.id,
                email=doc.email,
                speciality_id=doc.speciality_id,
                is_active=doc.is_active,
                doctor_status=doc.doctor_state,
                date_joined=doc.date_joined
            ) for doc in schedule.doctors
        ]

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=schedule.id,
                day=schedule.day,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                doctors=doctors_by_schedule_serialized
            ).model_dump(),
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@schedules.get("/available/days/{speciality_id}", response_model=AvailableSchedules)
async def days_by_availability(request: Request, speciality_id: UUID, session_db: SessionDep):
    try:
        speciality = session_db.get(Specialties, speciality_id)

        dict_days = {}

        for doc in speciality.doctors:
            for schedule in doc.medical_schedules:
                if schedule.available:
                    if dict_days.get(schedule.day.value, None):
                        match dict_days[schedule.day.value]:
                            case (start, end) if start > schedule.start_time and end > schedule.end_time:
                                dict_days[schedule.day.value] = (
                                    schedule.start_time,
                                    end
                                )

                            case (start, end) if start < schedule.start_time and end < schedule.end_time:
                                dict_days[schedule.day.value] = (
                                    start,
                                    schedule.end_time
                                )

                            case (start, end) if start < schedule.start_time and end > schedule.end_time:
                                continue
                    else:
                        dict_days.setdefault(
                            schedule.day.value,
                            (
                                schedule.start_time,
                                schedule.end_time
                            )
                        )

        return ORJSONResponse(
            AvailableSchedules(
                available_days=[
                    Schedules(
                        day=k,
                        start_time=v[0],
                        end_time=v[1]
                    ).model_dump() for k, v in dict_days.items()
                ]
            ).model_dump(),
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@schedules.post("/add/", response_model=MedicalScheduleResponse)
async def add_schedule(medical_schedule: MedicalScheduleCreate, session_db: SessionDep):
    schedule = MedicalSchedules(
        day=medical_schedule.day,
        start_time=medical_schedule.start_time,
        end_time=medical_schedule.end_time,
    )
    session_db.add(schedule)
    session_db.commit()
    session_db.refresh(schedule)

    doctors = []
    for doc in schedule.doctors:
        doctors.append(
            DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id
            ).model_dump()
        )

    return ORJSONResponse(
        MedicalScheduleResponse(
            id=schedule.id,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            doctors=doctors
        ).model_dump(),
        status_code=status.HTTP_201_CREATED
    )

@schedules.delete("/delete/{schedule_id}/", response_model=MedicalScheduleDelete)
async def delete_schedule(session_db: SessionDep, schedule_id: UUID):
    statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule_id)
    result: MedicalSchedules = session_db.exec(statement).first()

    if result:
        session_db.add(result)
        session_db.commit()

        return ORJSONResponse(
            MedicalScheduleDelete(
                id=result.id,
                message=f"Schedule {result.id} deleted"
            ).model_dump(),
            status_code=status.HTTP_202_ACCEPTED
        )
    else:
        return ORJSONResponse({
            "error": f"Schedule {result.id} not found"
        }, status_code=status.HTTP_404_NOT_FOUND)

@schedules.put("/add/doctor/", response_model=MedicalScheduleResponse)
async def add_doctor_by_id(session_db: SessionDep, doc_id: UUID = Query(...), schedule_id: UUID = Query(...)):
    try:
        statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule_id)
        schedule: MedicalSchedules = session_db.exec(statement).first()
        statement = select(Doctors).where(Doctors.id == doc_id)
        doctor: Doctors = session_db.exec(statement).first()

        schedule.doctors.append(doctor)

        session_db.add(schedule)
        session_db.commit()
        session_db.refresh(schedule)

        serial_docs: List[DoctorResponse] = []

        for doc in schedule.doctors:
            serial_docs.append(DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id
            ))

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=schedule.id,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                day=schedule.day,
                doctors=serial_docs
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        return ORJSONResponse({
            "error": str(e),
        }, status_code=400)

@schedules.put("/update/")
async def update_schedule(schedule: MedicalScheduleUpdate, session_db: SessionDep):
    """
    An enumeration of the days of the week.

    The `day` field must be one of the following string values:
      - "Monday"
      - "Tuesday"
      - "Wednesday"
      - "Thursday"
      - "Friday"
      - "Saturday"
      - "Sunday"

    Usage:
        {
            "day": "Monday",
        }
        Code:
            ```
            day = DayOfWeek.Monday.value
            ```

    Validation:
        When assigning to a `day` variable or accepting user input,
        ensure that the provided string matches exactly one of the
        above values. For example:

        ```python
        def set_meeting_day(day: str):
            try:
                selected_day = DayOfWeek(day)
            except ValueError:
                raise ValueError(f "Invalid day: {day}. Must be one of {list(DayOfWeek)}")
            # proceed with selected_day
        ```
    """
    try:
        statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule.id)
        result: MedicalSchedules = session_db.exec(statement).first()

        form_fields: List[str] = MedicalScheduleUpdate.__fields__.keys()

        for field in form_fields:
            value = getattr(schedule, field, None)
            if value is not None and field != "username":
                setattr(result, field, value)

        session_db.add(result)
        session_db.commit()
        session_db.refresh(result)

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=result.id,
                start_time=result.start_time,
                end_time=result.end_time,
                day=result.day,
            ).model_dump(),
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Schedule {schedule.id} not found")

doctors = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    default_response_class=ORJSONResponse,
    dependencies=[
        Depends(auth)
    ]
)

@doctors.get("/", response_model=List[DoctorResponse])
async def get_doctors(session_db: SessionDep):
    result: List[Doctors] = session_db.exec(
        select(Doctors).where(True)
    ).all()
    doctors_serialized = [DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id,
                blood_type=doc.blood_type,
                doctor_state=doc.doctor_state,
                address=doc.address,
            ).model_dump() for doc in result]

    return ORJSONResponse(doctors_serialized)

@doctors.get("/{doctor_id}/", response_model=DoctorResponse)
async def get_doctor_by_id(doctor_id: UUID, session_db: SessionDep):
    doc = session_db.get(Doctors, doctor_id)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")

    return ORJSONResponse(
        DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id,
            blood_type=doc.blood_type,
            schedules=[
                MedicalScheduleResponse(
                    id=schedule.id,
                    day=schedule.day,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                ) for schedule in doc.medical_schedules
            ]
        ).model_dump()
    )

@doctors.get("/me", response_model=DoctorResponse)
async def me_doctor(request: Request, session_db: SessionDep):
    doc: Doctors | User = request.state.user

    if isinstance(doc, User):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    doc = session_db.merge(doc)
    session_db.refresh(doc)

    return ORJSONResponse({
        "doc":DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id,
            blood_type=doc.blood_type,
            address=doc.address,
            doctor_state=doc.doctor_state,
            schedules=[
                MedicalScheduleResponse(
                    id=schedule.id,
                    day=schedule.day,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                ) for schedule in doc.medical_schedules
            ]
        ).model_dump(),
    })

@doctors.get("/{doctor_id}/patients", response_model=List[UserRead])
async def get_patients_by_doctor(
    request: Request,
    doctor_id: UUID,
    session_db: SessionDep,
    current_user: User | Doctors = Depends(require_doctor_or_admin),
):
    doc = session_db.get(Doctors, doctor_id)

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doctor {doctor_id} not found")

    if isinstance(current_user, Doctors):
        if current_user.id != doctor_id and not (current_user.is_admin or current_user.is_superuser):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif not (current_user.is_admin or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    users_map: Dict[UUID, User] = {}
    for appointment in doc.appointments or []:
        if not appointment or appointment.user is None:
            continue
        users_map[appointment.user.id] = appointment.user

    return ORJSONResponse(
        [
            UserRead(
                id=user.id,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                date_joined=user.date_joined,
                username=user.name,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                dni=user.dni,
                address=user.address,
                telephone=user.telephone,
                blood_type=user.blood_type,
                img_profile=user.url_image_profile
            ).model_dump() for user in users_map.values()
        ],
        status_code=status.HTTP_200_OK
    )
    
@doctors.get("/{doctor_id}/stats")
async def get_doctor_stats_by_id(request: Request, doctor_id: str, session_db: SessionDep):
    try:
        doctor_uuid = UUID(doctor_id)
    except ValueError as exc:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid doctor_id format") from exc

    doctor = await DoctorRepository.get_doctor_by_id(session_db, doctor_uuid)

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doctor {doctor_id} not found")

    try:
        metrics = await DoctorRepository.get_doctor_metrics(session_db, doctor)
    except ple.PolarsError as exc:
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error processing doctor metrics: {exc}",
        ) from exc
    except (KeyError, ValueError, TypeError) as exc:
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data for doctor metrics: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unexpected error calculating doctor metrics: {exc}",
        ) from exc

    if metrics is None or metrics == {}:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if isinstance(metrics, dict) and metrics.get("detail") == "No Data Found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No metrics found for doctor")

    return ORJSONResponse(
        metrics,
        status_code=status.HTTP_200_OK
    )

@doctors.post("/add/", response_model=DoctorResponse)
async def add_doctor(request: Request, doctor: DoctorCreate, session_db: SessionDep):
    try:
        user: User = request.state.user

        if not user.is_superuser and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

        new_doctor: Doctors = Doctors(
            email=doctor.email,
            name=doctor.username,
            telephone=doctor.telephone,
            last_name=doctor.last_name,
            dni=doctor.dni,
            speciality_id=doctor.speciality_id,
            password=doctor.password,
            address=doctor.address,
            blood_type=doctor.blood_type,
            first_name=doctor.first_name,
            doctor_state=doctor.doctor_state
        )

        new_doctor.set_password(doctor.password)

        session_db.add(new_doctor)
        session_db.commit()
        session_db.refresh(new_doctor)

        return ORJSONResponse(
            DoctorResponse(
                id=new_doctor.id,
                is_active=new_doctor.is_active,
                is_admin=new_doctor.is_admin,
                is_superuser=new_doctor.is_superuser,
                last_login=new_doctor.last_login,
                date_joined=new_doctor.date_joined,
                username=new_doctor.name,
                email=new_doctor.email,
                first_name=new_doctor.first_name,
                last_name=new_doctor.last_name,
                dni=new_doctor.dni,
                telephone=new_doctor.telephone,
                speciality_id=new_doctor.speciality_id,
                address=new_doctor.address,
                blood_type=new_doctor.blood_type,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        print(e)
        return ORJSONResponse({
            "error": str(e)
        }, status_code=status.HTTP_400_BAD_REQUEST)

@doctors.delete("/delete/{doctor_id}/", response_model=DoctorDelete)
async def delete_doctor(request: Request, doctor_id: UUID, session_db: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doctor_id)
    result = session_db.exec(statement).first()
    if result:
        session_db.delete(result)
        session_db.commit()

        return ORJSONResponse(
            DoctorDelete(
                id=result.id,
                message=f"Doctor {doctor_id} deleted"
            ).model_dump()
        )
    else:
        return ORJSONResponse({
            "error": "Doctor not found"
        },status_code=404)

@doctors.delete("/delete/{doctor_id}/schedule/{schedule_id}/", response_model=DoctorResponse)
async def delete_doctor_schedule_by_id(request: Request, schedule_id: UUID, doctor_id: UUID, session_db: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    doc: Doctors = session_db.exec(
        select(Doctors)
        .where(Doctors.id == doctor_id)
    ).first()

    doc.medical_schedules = [i for i in doc.medical_schedules if i.id != schedule_id]

    session_db.add(doc)
    session_db.commit()

    return ORJSONResponse(
        DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id
        ).model_dump()
    )

@doctors.patch("/update/{doctor_id}/", response_model=DoctorUpdate)
async def update_doctor(request: Request, doctor_id: UUID, session: SessionDep, doctor: Annotated[DoctorUpdate, Form(...)]):

    if not "doc" in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    if not request.state.user.id == doctor_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un unauthorized")

    try:
        doc = session.exec(
            select(Doctors)
            .where(Doctors.id == doctor_id)
        ).first()

        form_fields: List[str] = doctor.__fields__.keys()

        for field in form_fields:
            value = getattr(doctor, field, None)
            console.print(field," = ",value)
            if value is not None and field != "username" and not value in ["", " "]:
                setattr(doc, field, value)
            elif value is not None and field == "username" and not value in ["", " "]:
                doc.name = value
            elif value is not None and field == "doctor_state" and not value in ["", " "]:
                match value:
                    case DoctorStates.available.value:
                        doc.doctor_state = DoctorStates.available.value
                        doc.is_available = True

                    case DoctorStates.busy.value:
                        doc.doctor_state = DoctorStates.busy.value
                        doc.is_available = False

                    case DoctorStates.offline.value:
                        doc.doctor_state = DoctorStates.offline.value
                        doc.is_available = False
            else:
                continue

        session.add(doc)
        session.commit()
        session.refresh(doc)

        return ORJSONResponse(
            DoctorUpdate(
                username=doc.name,
                last_name=doc.last_name,
                first_name=doc.first_name,
                telephone=doc.telephone,
                email=doc.email,
                #speciality_id=doc.speciality_id,
                address=doc.address,
                doctor_state=doc.doctor_state
            ).model_dump()
        )

    except Exception:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")

@doctors.patch("/update/{doctor_id}/speciality", response_model=DoctorResponse)
async def update_speciality(request: Request, doctor_id: UUID, session: SessionDep, doctor_form: Annotated[DoctorSpecialityUpdate, Form(...)]):
    if not "doc" in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un un unauthorized")

    if not request.state.user.id == doctor_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un un unauthorized")

    try:
        doc = session.exec(
            select(Doctors)
            .where(Doctors.id == doctor_id)
        ).first()

        doc.speciality_id = doctor_form.speciality_id

        session.add(doc)
        session.commit()
        session.refresh(doc)

        return ORJSONResponse(
            DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                blood_type=doc.blood_type,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id
            ).model_dump()
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        print(e)
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")

@doctors.patch("/update/{doctor_id}/password")
async def update_doctor_password(request: Request, doctor_id: UUID, session: SessionDep, password: Annotated[DoctorPasswordUpdate, Form()]):
    if not "doc" in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    if not request.state.user.id == doctor_id and not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not un unauthorized")

    try:
        doc = session.exec(
            select(Doctors)
            .where(Doctors.id == doctor_id)
        ).first()

        doc.set_password(password.password)

        session.add(doc)
        session.commit()
        session.refresh(doc)

        return ORJSONResponse(
            DoctorUpdate(
                username=doc.name,
                last_name=doc.last_name,
                telephone=doc.telephone,
                email=doc.email,
                speciality_id=doc.speciality_id
            ).model_dump()
        )

    except Exception:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")

@doctors.patch("/add/schedule/", response_model=DoctorResponse)
async def add_schedule_by_id(request: Request, session: SessionDep, schedule_id: UUID = Query(...), doc_id: UUID = Query(...)):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        doc = session.exec(
            select(Doctors)
            .where(Doctors.id == doc_id)
        ).first()
        schedule = session.exec(
            select(MedicalSchedules)
            .where(MedicalSchedules.id == schedule_id)
        ).first()

        doc.medical_schedules.append(schedule)

        session.add(doc)
        session.commit()
        session.refresh(doc)

        return ORJSONResponse(
            DoctorResponse(
                id=doc.id,
                is_active=doc.is_active,
                is_admin=doc.is_admin,
                is_superuser=doc.is_superuser,
                last_login=doc.last_login,
                date_joined=doc.date_joined,
                username=doc.name,
                email=doc.email,
                first_name=doc.first_name,
                last_name=doc.last_name,
                dni=doc.dni,
                telephone=doc.telephone,
                speciality_id=doc.speciality_id
            ).model_dump()
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doc_id} not found")


@doctors.patch("/ban/{doc_id}/", response_model=DoctorResponse)
async def ban_doc(request: Request, doc_id: UUID, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doc_id)
    doc: Doctors = session.exec(statement).first()

    doc.is_active = True
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return ORJSONResponse({
        "doc":DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id
        ).model_dump(),
        "message":f"User {doc.name} has been banned."
    })

@doctors.patch("/unban/{doc_id}/", response_model=DoctorResponse)
async def unban_doc(request: Request, doc_id: UUID, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doc_id)
    doc: Doctors = session.exec(statement).first()

    doc.is_active = False
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return ORJSONResponse({
        "doc":DoctorResponse(
            id=doc.id,
            is_active=doc.is_active,
            is_admin=doc.is_admin,
            is_superuser=doc.is_superuser,
            last_login=doc.last_login,
            date_joined=doc.date_joined,
            username=doc.name,
            email=doc.email,
            first_name=doc.first_name,
            last_name=doc.last_name,
            dni=doc.dni,
            telephone=doc.telephone,
            speciality_id=doc.speciality_id
        ).model_dump(),
        "message":f"User {doc.name} has been unbanned."
    })

locations = APIRouter(
    prefix="/locations",
    tags=["locations"],
    dependencies=[
        Depends(auth)
    ]
)

@locations.get("/", response_model=List[LocationResponse])
async def get_locations(request: Request, session: SessionDep):
    statement = select(Locations).where(True)
    result_i: List[Locations] = session.exec(statement).all()
    locations_serialized: List["LocationResponse"] = [
        LocationResponse(
            id=location.id,
            name=location.name,
            description=location.description,
        ).model_dump() for location in result_i
    ]

    return locations_serialized

@locations.get("/all", response_model=List[LocationResponse])
async def get_locations_all_data(request: Request, session: SessionDep):
    statement = select(Locations).where(True)
    result_i: List[Locations] = session.exec(statement).all()
    locations_serialized: List["LocationResponse"] = []
    for location in result_i:
        #statement = select(Departments).where(Departments.location_id == location.id)
        result_i: List["Departments"] = location.departments #session.exec(statement).all()
        departments_serialized = []
        for department in result_i:
            #statement = select(Specialties).where(Specialties.department_id == department.id)
            result_ii: List["Specialties"] = department.specialities #session.exec(statement).all()
            specialties_serialized = []
            for specialty in result_ii:
                #statement = select(Services).where(Services.specialty_id == specialty.id)
                result_iii: List["Services"] = specialty.services #session.exec(statement).all()
                services_serialized: List["ServiceResponse"] = []
                for service in result_iii:
                    services_serialized.append(
                        ServiceResponse(
                            id=service.id,
                            name=service.name,
                            description=service.description,
                            price=service.price,
                            specialty_id=service.specialty_id,
                            icon_code=service.icon_code
                        )
                    )
                #statement = select(Doctors).where(Doctors.speciality_id == specialty.id)
                result_iiii: List["Doctors"] = specialty.doctors #session.exec(statement).all()
                doctors_serialized = []
                for doc in result_iiii:
                    doctors_serialized.append(
                        DoctorResponse(
                            id=doc.id,
                            is_active=doc.is_active,
                            is_admin=doc.is_admin,
                            is_superuser=doc.is_superuser,
                            last_login=doc.last_login,
                            date_joined=doc.date_joined,
                            username=doc.name,
                            email=doc.email,
                            first_name=doc.first_name,
                            last_name=doc.last_name,
                            dni=doc.dni,
                            telephone=doc.telephone,
                            speciality_id=doc.speciality_id,
                            blood_type=doc.blood_type
                        )
                    )
                specialties_serialized.append(
                    SpecialtyResponse(
                        id=specialty.id,
                        name=specialty.name,
                        description=specialty.description,
                        department_id=specialty.department_id,
                        services=services_serialized,
                        doctors=doctors_serialized,
                        icon_type=specialty.icon_code
                    )
                )
            departments_serialized.append(
                DepartmentResponse(
                    id=department.id,
                    name=department.name,
                    description=department.description,
                    location_id=department.location_id,
                    specialities=specialties_serialized
                )
            )
        locations_serialized.append(
            LocationResponse(
                id=location.id,
                name=location.name,
                description=location.description,
                departments=departments_serialized
            ).model_dump()
        )

    return ORJSONResponse({"locations_serialized":locations_serialized})

@locations.post("/add/", response_model=LocationResponse)
async def set_location(request: Request, session: SessionDep, location: LocationCreate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        new_location = Locations(
            name=location.name,
            description=location.description
        )

        session.add(new_location)
        session.commit()
        session.refresh(new_location)

        return ORJSONResponse(
            LocationResponse(
                id=new_location.id,
                name=new_location.name,
                description=new_location.description,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@locations.delete("/delete/{location_id}", response_model=LocationDelete)
async def delete_location(request: Request, location_id: UUID, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    location: Locations = session.exec(
        select(Locations)
        .where(Locations.id == location_id)
    ).first()

    session.delete(location)
    session.commit()

    return ORJSONResponse(
        LocationDelete(
            id=location.id,
            message=f"Location {location.name} deleted"
        ).model_dump()
    )

@locations.put("/update/{location_id}/", response_model=LocationResponse)
async def update_location(request: Request, location_id: UUID, session: SessionDep, location: LocationUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    new_location = session.exec(
        select(Locations)
        .where(Locations.id == location_id)
    ).first()

    new_location.name = location.name
    new_location.description = location.description

    session.add(new_location)
    session.commit()
    session.refresh(new_location)

    return ORJSONResponse(
        LocationResponse(
            id=new_location.id,
            name=new_location.name,
            description=new_location.description
        ).model_dump()
    )


services = APIRouter(
    prefix="/services",
    tags=["services"],
    dependencies=[
        Depends(auth)
    ]
)

@services.get("/", response_model=List[ServiceResponse])
async def get_services(request: Request, session: SessionDep):
    result: List["Services"] = session.exec(
        select(Services).where(True)
    ).all()
    services_serialized = [
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code
        ).model_dump() for service in result
    ]

    return ORJSONResponse(services_serialized, status_code=status.HTTP_200_OK)

@services.get("/{service_id}", response_model=ServiceResponse)
async def get_service_by_id(request: Request, service_id: UUID, session: SessionDep):
    service = session.get(Services, service_id)
    return ORJSONResponse(
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code
        ).model_dump(),
        status_code=status.HTTP_200_OK
    )

@services.post("/add", response_model=ServiceResponse)
async def set_service(request: Request, session: SessionDep, service: ServiceCreate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        new_service = Services(
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
            icon_code=service.icon_code
        )

        session.add(new_service)
        session.commit()
        session.refresh(new_service)

        return ORJSONResponse(
            ServiceResponse(
                id=new_service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id,
                icon_code=service.icon_code
            ).model_dump()
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        return ORJSONResponse({
            "error": str(e),
        }, status_code=status.HTTP_400_BAD_REQUEST)

@services.delete("/delete/{service_id}", response_model=ServiceDelete)
async def delete_service(request: Request, session: SessionDep, service_id :UUID):
    try:
        service = session.exec(select(Services).where(Services.id == service_id)).first()

        session.delete(service)
        session.commit()

        return ORJSONResponse(
            ServiceDelete(
                id=service.id,
                message=f"Service {service.name} has been deleted"
            ).model_dump()
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@services.patch("/update/{service_id}/", response_model=ServiceResponse)
async def update_service(
    request: Request,
    session: SessionDep,
    service_id: UUID,
    service: ServiceUpdate
):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=401, detail="Not authorized")

    new_service = session.get(Services, service_id)
    if not new_service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = service.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(new_service, key, value)
    
    session.add(new_service)
    session.commit()
    session.refresh(new_service)
    
    data = ServiceResponse(
        id=new_service.id,
        name=new_service.name,
        description=new_service.description,
        price=new_service.price,
        specialty_id=new_service.specialty_id,
    )
    
    return data




specialities = APIRouter(
    prefix="/specialities",
    tags=["specialities"],
    dependencies=[
        Depends(auth)
    ]
)

@specialities.get("/", response_model=List[SpecialtyResponse])
async def get_specialities(request: Request, session: SessionDep):
    statement = select(Specialties)
    result: List["Specialties"] = session.exec(statement).all()

    specialities_serialized: List[SpecialtyResponse] = []
    for speciality in result:
        result: List["Services"] = speciality.services

        services_serialized: List[ServiceResponse] = []
        for service in result:
            services_serialized.append(
                ServiceResponse(
                    id=service.id,
                    name=service.name,
                    description=service.description,
                    price=service.price,
                    specialty_id=service.specialty_id,
                    icon_code=service.icon_code
                )
            )

        statement = select(Doctors).where(Doctors.speciality_id == speciality.id)
        result: List["Doctors"] = session.exec(statement).all()

        doctors_serialized: List[DoctorResponse] = []
        for doc in result:
            doctors_serialized.append(
                DoctorResponse(
                    id=doc.id,
                    is_active=doc.is_active,
                    is_admin=doc.is_admin,
                    is_superuser=doc.is_superuser,
                    last_login=doc.last_login,
                    date_joined=doc.date_joined,
                    username=doc.name,
                    email=doc.email,
                    first_name=doc.first_name,
                    last_name=doc.last_name,
                    dni=doc.dni,
                    telephone=doc.telephone,
                    speciality_id=doc.speciality_id
                )
            )

        specialities_serialized.append(
            SpecialtyResponse(
                id=speciality.id,
                name=speciality.name,
                description=speciality.description,
                department_id=speciality.department_id,
                doctors=doctors_serialized,
                services=services_serialized
            ).model_dump()
        )

    return ORJSONResponse(
        specialities_serialized,
        status_code=status.HTTP_200_OK
    )


@specialities.post("/add/", response_model=SpecialtyResponse)
async def add_speciality(request: Request, session: SessionDep, specialty: SpecialtyCreate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        new_speciality = Specialties(
            name=specialty.name,
            description=specialty.description,
            department_id=specialty.department_id
        )

        session.add(new_speciality)
        session.commit()
        session.refresh(new_speciality)

        return ORJSONResponse(
            SpecialtyResponse(
                id=new_speciality.id,
                name=new_speciality.name,
                description=new_speciality.description,
                department_id=new_speciality.department_id
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@specialities.delete("/delete/{speciality_id}/", response_model=SpecialtyDelete)
async def delete_speciality(request: Request, session: SessionDep, speciality_id: UUID):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    speciality: Specialties = session.exec(
        select(Specialties)
        .where(Specialties.id == speciality_id)
    ).first()

    session.delete(speciality)
    session.commit()

    return ORJSONResponse(
        SpecialtyDelete(
            id=speciality.id,
            message=f"Specialty {speciality.name} has been deleted"
        ).model_dump()
    )

@specialities.patch("/update/{speciality_id}/", response_model=SpecialtyResponse)
async def update_speciality(request: Request, session: SessionDep, speciality_id: UUID, speciality: SpecialtyUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    new_speciality: Services = session.exec(
        select(Specialties).where(Specialties.id == speciality_id)
    ).first()

    fields = speciality.__fields__.keys()

    for field in fields:
        value = getattr(speciality, field)
        if value is not None:
            setattr(new_speciality, field, value)

    session.add(new_speciality)
    session.commit()
    session.refresh(new_speciality)

    return ORJSONResponse(
        SpecialtyResponse(
            id=new_speciality.id,
            name=new_speciality.name,
            description=new_speciality.description,
            department_id=new_speciality.department_id
        ).model_dump()
    )

chat = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ConnectionManager:
    """
    Gestor de conexiones WebSocket para chat en tiempo real entre médicos.
    
    Mantiene registro de conexiones activas, permite envío de mensajes
    personales y broadcast, y gestiona el ciclo de vida de las conexiones.
    
    Attributes:
        active_connections (dict): Mapeo de user_id a WebSocket activos
    """
    
    def __init__(self):
        """Inicializa el gestor con diccionario vacío de conexiones."""
        self.active_connections: dict[UUID, WebSocket] = {}  # user_id → WebSocket

    async def connect(self, user_id: UUID, websocket: WebSocket):
        """
        Establece una nueva conexión WebSocket.
        
        Acepta el handshake WebSocket y registra la conexión activa
        para el usuario especificado.
        
        Args:
            user_id (UUID): ID del usuario que se conecta
            websocket (WebSocket): Instancia de la conexión WebSocket
        """
        await websocket.accept()  # Handshake HTTP→WS :contentReference[officiate:4]{index=4}
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: UUID):
        """
        Cierra y elimina una conexión WebSocket.
        
        Args:
            user_id (UUID): ID del usuario a desconectar
        """
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: UUID):
        """
        Envía mensaje directo a un usuario específico.
        
        Args:
            message (dict): Mensaje en formato JSON a enviar
            user_id (UUID): ID del usuario destinatario
            
        Note:
            Si el usuario no está conectado, el mensaje se pierde.
        """
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)  # envía JSON → cliente :contentReference[officiate:5]{index=5}

    async def broadcast(self, message: dict):
        """
        Envía mensaje a todas las conexiones activas.
        
        Args:
            message (dict): Mensaje en formato JSON para broadcast
        """
        for ws in self.active_connections.values():
            await ws.send_json(message)

    def is_connected(self, doc_id) -> bool:
        """
        Verifica si un médico está conectado.
        
        Args:
            doc_id: ID del médico a verificar
            
        Returns:
            bool: True si está conectado, False en caso contrario
        """
        return doc_id in self.active_connections


manager = ConnectionManager()

@chat.get("/", response_model=List[ChatResponse])
async def get_chats(session: SessionDep):
    try:
        chats: List[Chat] = session.exec(
            select(Chat)
        ).all()

        chats_list: List["ChatResponse"] = []
        for chat_i in chats:
            doctor_1: Doctors = session.exec(
                select(Doctors).where(Doctors.id == chat_i.doc_1_id)
            ).first()
            doctor_2: Doctors = session.exec(
                select(Doctors).where(Doctors.id == chat_i.doc_2_id)
            ).first()

            chats_list.append(
                ChatResponse(
                    id=chat_i.id,
                    doc_1=DoctorResponse(
                        id=doctor_1.id,
                        is_active=doctor_1.is_active,
                        is_admin=doctor_1.is_admin,
                        is_superuser=doctor_1.is_superuser,
                        last_login=doctor_1.last_login,
                        date_joined=doctor_1.date_joined,
                        username=doctor_1.name,
                        email=doctor_1.email,
                        first_name=doctor_1.first_name,
                        last_name=doctor_1.last_name,
                        dni=doctor_1.dni,
                        telephone=doctor_1.telephone,
                        speciality_id=doctor_1.speciality_id
                    ),
                    doc_2=DoctorResponse(
                        id=doctor_2.id,
                        is_active=doctor_2.is_active,
                        is_admin=doctor_2.is_admin,
                        is_superuser=doctor_2.is_superuser,
                        last_login=doctor_2.last_login,
                        date_joined=doctor_2.date_joined,
                        username=doctor_2.name,
                        email=doctor_2.email,
                        first_name=doctor_2.first_name,
                        last_name=doctor_2.last_name,
                        dni=doctor_2.dni,
                        telephone=doctor_2.telephone,
                        speciality_id=doctor_2.speciality_id
                    )
                ).model_dump()
            )

        return ORJSONResponse(
            chats_list,
        )

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail=str(e))

@chat.post("/add")
async def create_chat(request: Request, session: SessionDep, doc_2_id=Query(...), _=Depends(auth)):
    if not "doc" in request.state.scopes:
        raise HTTPException(status_code=401, detail="Unauthorized")

    doc: Doctors = request.state.user
    
    console.print(doc)
    console.print(request.state.scopes)

    if isinstance(doc, User):
        raise HTTPException(status_code=403, detail="You are not authorized")

    new_chat = Chat(
        doc_1_id=doc.id,
        doc_2_id=doc_2_id,
    )

    session.add(new_chat)
    session.commit()
    session.refresh(new_chat)

    return ORJSONResponse({
        "message":f"Chat {new_chat.id} created"
    }, status_code=status.HTTP_200_OK)

ws_chat = APIRouter(
    prefix="/ws"
)

@ws_chat.websocket("/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, session: SessionDep, chat_id, data: tuple = Depends(ws_auth)):
    #console.print(data)
    if data is None:
    #    await websocket.close(1008, reason="Data Error")
        raise WebSocketDisconnect()

    if not "doc" in data[1]:
        await websocket.close(1008, reason="Unauthorized")

    doc: Doctors = data[0]

    try:
        if isinstance(doc, User):
            await websocket.close(1008, reason="You are not authorized")

        chat_db: Chat = session.exec(select(Chat).where(Chat.id == chat_id)).first()

        if chat_db.doc_1_id != doc.id and chat_db.doc_2_id != doc.id:
            await websocket.close(1008, reason="doctor unauthorized")

    except Exception:
        console.print_exception(show_locals=True)
        await websocket.close(1008, reason="unknown error")

    await manager.connect(doc.id, websocket)
    try:
        console.rule("send message")
        #await manager.broadcast({"type":"presence","user":str(doc.id),"status":"online"})
        while True:
            data = await websocket.receive_json()
            content = data["content"]

            chat_db: Chat = session.exec(select(Chat).where(Chat.id == chat_id)).first()
            
            console.print(f"Chat: {chat_db}")

            message = ChatMessages(
                sender_id=doc.id,
                chat_id=chat_id,
                content=content,
                chat=chat_db,
            )
            
            console.print(f"Message: {message}")

            session.add(message)
            session.commit()
            session.refresh(message)
            
            console.rule("Fin Message")

            if manager.is_connected(doc.id):
                await manager.send_personal_message({
                    "type":"message",
                    "message":{
                        "content":message.content,
                        "created_at":message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    },
                }, user_id=chat_db.doc_2_id)

    except WebSocketDisconnect:
        pass

    #finally:
    #    await manager.broadcast({"type":"presence","user":str(doc.id),"status":"offline"})
    #    manager.disconnect(doc.id)


turns = APIRouter(
    prefix="/turns",
    tags=["turns"],
    dependencies=[
        Depends(auth)
    ]
)

@turns.get("/", response_model=List[TurnsResponse])
async def get_turns(request: Request, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=401, detail="You are not authorized")

    statement = select(Turns).options(
        selectinload(Turns.payment).selectinload(Payment.items),
        selectinload(Turns.services),
        selectinload(Turns.doctor),
    )
    result: List["Turns"] = session.exec(statement).all()

    turns_serialized: List[TurnsResponse] = []
    for turn in result:
        turns_serialized.append(
            TurnsResponse(
                id=turn.id,
                reason=turn.reason,
                state=turn.state,
                date=turn.date,
                date_limit=turn.date_limit,
                date_created=turn.date_created,
                user_id=turn.user_id,
                doctor_id=turn.doctor_id,
                appointment_id=str(turn.appointment.id),
                time=turn.time,
                payment=(
                    PaymentRead.model_validate(turn.payment, from_attributes=True)
                    if turn.payment
                    else None
                ),
                service=[
                    ServiceResponse(
                        id=serv.id,
                        name=serv.name,
                        description=serv.description,
                        price=serv.price,
                        specialty_id=serv.specialty_id
                    ) for serv in turn.services
                ]
            ).model_dump()
        )

    return ORJSONResponse(turns_serialized)

Serializer = TypeVar("Serializer")

def serialize_model(model: object, serializer: Serializer, session, refresh: bool = False) -> Serializer:
    """
    Serializa un modelo de base de datos usando un schema específico.
    
    Función helper para convertir modelos SQLModel en schemas Pydantic,
    copiando campos automáticamente entre el modelo y el serializer.
    
    Args:
        model (object): Instancia del modelo de base de datos
        serializer (Serializer): Clase del schema Pydantic
        session: Sesión de base de datos para refresh opcional
        refresh (bool): Si refrescar el modelo desde la BD
        
    Returns:
        Serializer: Instancia del schema con datos del modelo
        
    Note:
        - Copia todos los campos definidos en el serializer
        - Útil para automatizar conversión modelo → schema
        - TypeVar Serializer mantiene type safety
    """
    fields = serializer.__fields__.keys()
    serializer_f = serializer()
    for i in fields:
        setattr(serializer_f, i, getattr(model, i))


@turns.get("/{user_id}", response_model=Optional[List[TurnsResponse]])
async def get_turns_by_user_id(request: Request, session: SessionDep, user_id: UUID):
    user = session.get(User, user_id)

    def serialize_departament(d: Departments):
        session.merge(d)
        session.refresh(d)
        return DepartmentResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            location_id=d.location_id,
        )

    def serialize_speciality(s: Specialties):
        session.merge(s)
        session.refresh(s)
        return SpecialtyResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            department_id=s.department_id,
            department=serialize_departament(s.departament)
        )

    try:
        turns_serialized = [
            TurnsResponse(
                id=turn.id,
                reason=turn.reason,
                state=turn.state,
                date=turn.date,
                date_limit=turn.date_limit,
                date_created=turn.date_created,
                user_id=turn.user_id,
                time=turn.time,
                payment=(
                    PaymentRead.model_validate(turn.payment, from_attributes=True)
                    if turn.payment
                    else None
                ),
                doctor=DoctorResponse(
                    id=turn.doctor.id,
                    dni=turn.doctor.dni,
                    username=turn.doctor.name,
                    speciality_id=turn.doctor.speciality_id,
                    date_joined=turn.doctor.date_joined,
                    is_active=turn.doctor.is_active,
                    email=turn.doctor.email,
                    first_name=turn.doctor.first_name,
                    last_name=turn.doctor.last_name,
                    telephone=turn.doctor.telephone
                ).model_dump(),
                service=[
                    ServiceResponse(
                        id=service.id,
                        name=service.name,
                        description=service.description,
                        price=service.price,
                        specialty_id=service.specialty_id,
                    ).model_dump() for service in turn.services
                ]
            ).model_dump() for turn in user.turns
        ]

        return ORJSONResponse(
            turns_serialized,
            status_code=200,
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@turns.get("/{turn_id}", response_model=TurnsResponse)
async def get_turn_by_id(request: Request, session: SessionDep, turn_id: UUID):
    user = request.state.user

    try:
        secure_turn: Turns = session.exec(
            select(Turns)
            .where(Turns.id == turn_id)
        ).first()

        if secure_turn is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

        if secure_turn.user_id != user.id or secure_turn.doctor_id != user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        return ORJSONResponse(
            TurnsResponse(
                id=secure_turn.id,
                reason=secure_turn.reason,
                state=secure_turn.state,
                date=secure_turn.date,
                date_limit=secure_turn.date_limit,
                date_created=secure_turn.date_created,
                user_id=secure_turn.user_id,
                payment=(
                    PaymentRead.model_validate(secure_turn.payment, from_attributes=True)
                    if secure_turn.payment
                    else None
                ),
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@turns.post("/add", response_model=PayTurnResponse)
async def create_turn(request: Request, session: SessionDep, turn: TurnsCreate):
    user: User | None = request.state.user
    scopes = getattr(request.state, "scopes", []) or []
    doctor: Doctors | None = None

    if "doc" in scopes:
        if turn.user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

        if isinstance(user, Doctors):
            doctor = user
        elif user:
            doctor = session.get(Doctors, user.id)

        if doctor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated doctor not found")

        if turn.doctor_id is None:
            turn.doctor_id = doctor.id
        elif turn.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="doctor_id must match the authenticated doctor")

    elif user:
        turn.user_id = user.id

    else:
        raise HTTPException(status_code=500, detail="Internal Error")

    patient = session.get(User, turn.user_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if turn.doctor_id:
        doctor = doctor or session.get(Doctors, turn.doctor_id)
        if doctor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    try:
        new_turn, new_appointment = await TurnAndAppointmentRepository.create_turn_and_appointment(
            session=session,
            turn=turn,
            doctor=doctor
        )

        if not new_turn:
            lowered_message = (new_appointment or "").lower()

            status_code_error = status.HTTP_409_CONFLICT
            if "schedule" in lowered_message or "agenda" in lowered_message:
                status_code_error = status.HTTP_404_NOT_FOUND
            elif "service" in lowered_message or "doctor" in lowered_message:
                status_code_error = status.HTTP_400_BAD_REQUEST

            raise HTTPException(status_code=status_code_error, detail=new_appointment)

        payment_service = PaymentService(session)
        payment = await payment_service.create_payment_for_turn(
            turn=new_turn,
            appointment=new_appointment,
            user=patient,
            payment_method=PaymentMethod.card,
            gateway_metadata={"health_insurance": str(turn.health_insurance)}
            if turn.health_insurance
            else None,
            health_insurance_id=turn.health_insurance,
        )

        payment_read = PaymentRead.model_validate(payment, from_attributes=True)

        return ORJSONResponse(
            PayTurnResponse(
                turn=TurnsResponse(
                    id=new_turn.id,
                    reason=new_turn.reason,
                    state=new_turn.state,
                    date=new_turn.date,
                    date_limit=new_turn.date_limit,
                    date_created=new_turn.date_created,
                    user_id=new_turn.user_id,
                    time=new_turn.time
                ).model_dump(),
                payment=payment_read,
                payment_url=payment.payment_url
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
        
    except HTTPException as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@turns.delete("/delete/{turn_id}", response_model=TurnsDelete)
async def delete_turn(request: Request, session: SessionDep, turn_id: UUID):
    session_user = request.state.user
    try:
        turn = session.get(Turns, turn_id)
        if session_user.id != turn.user_id or session_user.id != turn.doctor_id:
            raise HTTPException(status_code=403, detail="You are not authorized")
        deleted = TurnAndAppointmentRepository.delete_turn_and_appointment(session, turn)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"the turn: {turn_id} cannot be deleted")
        return ORJSONResponse(
            TurnsDelete(
                id=turn.id,
                message=f"Turn {turn.id} has been deleted"
            ),
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@turns.patch("/update/state")
async def update_state(request: Request, turn_id: UUID, new_state: str, session: SessionDep):
    turn = session.get(Turns, turn_id)

    if not turn:
        raise HTTPException(404, detail="Turn Not Found")

    if "superuser" not in request.state.scopes:
        if turn.state.value in ["finished", "rejected", "cancelled"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Turn has a not mutable state")

    try:

        match new_state:
            case "waiting":
                turn.state = TurnsState.waiting

            case "finished":
                turn.state = TurnsState.finished

            case "cancelled":
                turn.state = TurnsState.cancelled

            case "rejected":
                turn.state = TurnsState.rejected

            case "accepted":
                turn.state = TurnsState.accepted

            case _:
                raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=f"{new_state} isn´t in the valid states")

        session.add(turn)
        session.commit()

        return ORJSONResponse({
            "msg":"success"
        },status_code=200)

    except HTTPException as e:
        raise HTTPException from e

    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(500, detail=str(e))

# TODO: hacer los patchs

appointments = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    dependencies=[
        Depends(auth)
    ]
)


def _get_primary_service(turn) -> Tuple[Optional[UUID], Optional[dict]]:
    """Return first service associated with a turn, if any."""

    if not turn or not turn.services:
        return None, None

    service = turn.services[0]
    serialized_service = ServiceResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        price=service.price,
        specialty_id=service.specialty_id,
        icon_code=service.icon_code,
    ).model_dump()

    return service.id, serialized_service


@appointments.get("/", response_model=List[AppointmentResponse])
async def get_appointments(request: Request, session: SessionDep):
    if not request.state.user.is_superuser and not "doc" in request.state.scopes:
        raise HTTPException(status_code=401, detail="You are not authorized")

    statement = select(Appointments)
    result: List["Appointments"] = session.exec(statement).all()
    serialized_appointments: List[AppointmentResponse] = []
    for appointment in result:
        service_id, serialized_service = _get_primary_service(appointment.turn)
        serialized_appointments.append(
            AppointmentResponse(
                id=appointment.id,
                user_id=appointment.user_id,
                doctor_id=appointment.doctor_id,
                turn_id=appointment.turn_id,
                service_id=service_id,
                date=appointment.turn.date,
                date_created=appointment.turn.date_created,
                date_limit=appointment.turn.date_limit,
                state=appointment.turn.state,
                service=serialized_service,
            ).model_dump()
        )

    return ORJSONResponse(serialized_appointments)

health_insurance = APIRouter(
    prefix="/health_insurance",
    tags=["health_insurance"],
    dependencies=[
        Depends(auth),
    ]
)

@health_insurance.get("/", response_model=List[HealthInsuranceRead])
async def get_health_insurance(request: Request, session: SessionDep):
    result = session.exec(
        select(HealthInsurance)
    ).all()

    serialized_heath_insurance: List[HealthInsuranceRead] = []
    for i in result:
        serialized_heath_insurance.append(
            HealthInsuranceRead(
                id=i.id,
                name=i.name,
                description=i.description,
                discount=i.discount
            ).model_dump()
        )

    return serialized_heath_insurance

@health_insurance.get("/detail/{hi_id}", response_model=HealthInsuranceRead)
async def get_health_insurance(
        request: Request,
        session: SessionDep,
        hi_id: UUID,
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data

@health_insurance.post("/create", response_model=HealthInsuranceRead, status_code=status.HTTP_201_CREATED)
async def create_health_insurance(
        request: Request,
        session: SessionDep,
        payload: HealthInsuranceCreate,
):
    hi = HealthInsurance.model_validate(payload)
    session.add(hi)
    session.commit()
    session.refresh(hi)
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data

@health_insurance.patch("/update/{hi_id}", response_model=HealthInsuranceRead)
async def update_health_insurance(
        request: Request,
        session: SessionDep,
        hi_id: UUID,
        payload: HealthInsuranceUpdate,
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hi, key, value)
    session.add(hi)
    session.commit()
    session.refresh(hi)
    data = HealthInsuranceRead(
        id=hi.id,
        name=hi.name,
        description=hi.description,
        discount=hi.discount,
    ).model_dump()
    return data

@health_insurance.delete("/delete/{hi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_insurance(
        request: Request,
        session: SessionDep,
        hi_id: UUID,
):
    hi = session.get(HealthInsurance, hi_id)
    if not hi:
        raise HTTPException(status_code=404, detail="HealthInsurance not found")
    session.delete(hi)
    session.commit()
    return ORJSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

chat.include_router(ws_chat)

router = APIRouter(
    prefix="/medic",
    default_response_class=ORJSONResponse,
)

router.include_router(schedules)
router.include_router(doctors)
router.include_router(locations)
router.include_router(services)
router.include_router(specialities)
router.include_router(chat)
router.include_router(departments)
router.include_router(turns)
router.include_router(appointments)
router.include_router(health_insurance)