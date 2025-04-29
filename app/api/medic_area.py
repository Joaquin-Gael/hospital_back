from fastapi import (
    APIRouter,
    Request,
    Query,
    status,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException
)
from fastapi.responses import ORJSONResponse

from sqlmodel import select

from typing import List

from rich import print
from rich.console import Console

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
)
from app.schemas.medica_area import (
    MedicalScheduleCreate,
    MedicalScheduleDelete,
    MedicalScheduleUpdate,
    MedicalScheduleResponse
)
from app.schemas.medica_area import (
    DayOfWeek,
    TurnsState
)
from app.schemas.medica_area import (
    DoctorResponse,
    DoctorCreate,
    DoctorDelete,
    DoctorUpdate
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
from app.db.main import SessionDep
from app.core.auth import JWTBearer, JWTWebSocket

auth = JWTBearer(auto_error=False)
ws_auth = JWTWebSocket()

console = Console()

departments = APIRouter(
    prefix="/departments",
    tags=["departments"],
    default_response_class=ORJSONResponse,
    dependencies=[
        Depends(auth)
    ]
)

@departments.get("/", response_model=DepartmentResponse)
async def get_departments(request: Request, session: SessionDep):
    result = session.execute(
        select(Departments)
    )

    departments_list: List[DepartmentResponse] = []
    for department in result:
        departments_list.append(
            DepartmentResponse(
                id=department.id,
                name=department.name,
                description=department.description,
                location_id=department.location_id
            ).model_dump()
        )

    return departments_list

@departments.get("/{department_id}/", response_model=DepartmentResponse)
async def get_department_by_id(request: Request, department_id: int, session: SessionDep):
    department = session.execute(
        select(Departments).where(Departments.id == department_id)
    ).scalars().first()

    return DepartmentResponse(
        id=department.id,
        name=department.name,
        description=department.description,
        location_id=department.location_id
    ).model_dump()

@departments.post("/add/", response_model=DepartmentResponse)
async def add_department(request: Request, department: DepartmentCreate, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    new_department: Departments = Departments(
        id=department.id,
        name=department.name,
        description=department.description,
        location_id=department.location_id
    )

    session.add(new_department)
    session.commit()
    session.refresh(new_department)

    return DepartmentResponse(
        id=new_department.id,
        name=new_department.name,
        description=new_department.description,
        location_id=new_department.location_id
    ).model_dump()

@departments.delete("/delete/{department_id}/", response_model=DepartmentDelete)
async def delete_department_by_id(request: Request, department_id: int, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        department: Departments = session.execute(
            select(Departments).where(Departments.id == department_id)
        ).scalars().first()

        session.delete(department)
        session.commit()
        session.refresh(department)

        return DepartmentDelete(
            id=department.id,
            message=f"Department {department.name} has been deleted"
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department {department_id} not found")


@departments.patch("/update/{department_id}/", response_model=DepartmentResponse)
async def update_department(request: Request, department_id: str , department: DepartmentUpdate, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    new_department: Departments = session.execute(
        select(Departments).where(Departments.id == department_id)
    ).scalars().first()

    new_department.name = department.name
    new_department.description = department.description
    new_department.location_id = department.location_id

    session.add(new_department)
    session.commit()
    session.refresh(new_department)

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
async def get_medical_schedules(request: Request, session: SessionDep):
    statement = select(MedicalSchedules)
    result: List[MedicalSchedules] = session.execute(statement).scalars().all()
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
                speciality_id=doc.speciality_id
            )
            doctors.append(doctor)
        schedule = MedicalScheduleResponse(
            id=schedule_i.id,
            day=schedule_i.day,
            time_medic=schedule_i.time_medic,
            doctors=doctors
        )
        schedules.append(schedule.model_dump())

    return ORJSONResponse(
        schedules
    )

@schedules.post("/add/", response_model=MedicalScheduleResponse)
async def add_schedule(medical_schedule: MedicalScheduleCreate, session: SessionDep):
    schedule = MedicalSchedules(
        day=medical_schedule.day,
        start_time=medical_schedule.start_time,
        end_time=medical_schedule.end_time,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

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
async def delete_schedule(session: SessionDep, schedule_id: str):
    statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule_id)
    result: MedicalSchedules = session.execute(statement).scalars().first()

    if result:
        session.delete(result)
        session.commit()
        session.refresh(result)

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
async def add_doctor_by_id(session: SessionDep, doc_id: str = Query(...), schedule_id: str = Query(...)):
    try:
        statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule_id)
        schedule: MedicalSchedules = session.execute(statement).scalars().first()
        statement = select(Doctors).where(Doctors.id == doc_id)
        doctor: Doctors = session.execute(statement).scalars().first()

        schedule.doctors.append(doctor)

        session.add(schedule)
        session.commit()
        session.refresh(schedule)

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
async def update_schedule(schedule: MedicalScheduleUpdate, session: SessionDep):
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
                raise ValueError(f"Invalid day: {day}. Must be one of {list(DayOfWeek)}")
            # proceed with selected_day
        ```
    """
    try:
        statement = select(MedicalSchedules).where(MedicalSchedules.id == schedule.id)
        result: MedicalSchedules = session.execute(statement).scalars().first()

        form_fields: List[str] = MedicalScheduleUpdate.__fields__.keys()

        for field in form_fields:
            value = getattr(schedule, field, None)
            if value is not None and field != "username":
                setattr(result, field, value)

        session.add(result)
        session.commit()
        session.refresh(result)

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
async def get_doctors(request: Request, session: SessionDep):
    statement = select(Doctors)
    result: List[Doctors] = session.execute(statement).scalars().all()
    doctors = []
    for doc in result:
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

    return ORJSONResponse(doctors)

@doctors.get("/{doctor_id}/", response_model=DoctorResponse)
async def get_doctor_by_id(request: Request, dotor_id: str, session: SessionDep):
    statement = select(Doctors).where(Doctors.id == dotor_id)
    doc = session.execute(statement).scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Doctor {dotor_id} not found")

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
        )
    )

@doctors.get("/me/", response_model=DoctorResponse)
async def me_doctor(request: Request):
    doc: Doctors | User = request.state.user

    if isinstance(doc, User):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    schedules: List["MedicalScheduleResponse"] = []
    for schedule in doc.medical_schedules:
        schedules.append(
            MedicalScheduleResponse(
                id=schedule.id,
                time_medic=schedule.time_medic,
                day=schedule.day,
            )
        )

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
        ),
        "schedules":schedules
    })

@doctors.post("/add/", response_model=DoctorResponse)
async def add_doctor(request: Request, doctor: DoctorCreate, session: SessionDep):
    try:
        user: User = request.state.user

        if not user.is_superuser and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

        new_doctor: Doctors = Doctors(
            id=doctor.id,
            email=doctor.email,
            name=doctor.name,
            telephone=doctor.telephone,
            lastname=doctor.lastname,
            dni=doctor.dni,
            speciality_id=doctor.speciality_id,
            password=doctor.password,
        )

        new_doctor.set_password(doctor.password)

        session.add(new_doctor)
        session.commit()
        session.refresh(new_doctor)

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
                speciality_id=new_doctor.speciality_id
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
async def delete_doctor(request: Request, doctor_id: str, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doctor_id)
    result = session.execute(statement).scalars().first()
    if result:
        session.delete(result)
        session.commit()
        session.refresh(result)
        return ORJSONResponse(DoctorDelete(id=result.id, message=f"Doctor {doctor_id} deleted"))
    else:
        return ORJSONResponse({
            "error": "Doctor not found"
        },status_code=404)

@doctors.delete("/delete/{doctor_id}/schedule/{schedule_id}/", response_model=DoctorResponse)
async def delete_doctor_schedule_by_id(request: Request, schedule_id: str, doctor_id: str, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    doc: Doctors = session.execute(
        select(Doctors)
            .where(Doctors.id == doctor_id)
    ).scalars().first()

    doc.medical_schedules = [i for i in doc.medical_schedules if i.id != schedule_id]

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
        )
    )

@doctors.put("/update/{doctor_id}/", response_model=DoctorUpdate)
async def update_doctor(request: Request, doctor_id: str, session: SessionDep, doctor: DoctorUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        doc = session.excecute(
            select(Doctors)
                .where(Doctors.id == doctor_id)
        ).scalars().first()

        form_fields: List[str] = list(DoctorUpdate.__fields__.keys())


        for field in form_fields:
            value = getattr(doctor, field, None)
            if value is not None and field != "username":
                setattr(doc, field, value)
            elif field == "username":
                doc.name = getattr(doctor, field)
            elif field == "password":
                doc.set_password(doctor.password)

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
            )
        )

    except Exception:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")

@doctors.put("/add/schedule/", response_model=DoctorResponse)
async def add_schedule_by_id(request: Request, session: SessionDep, schedule_id: str = Query(...), doc_id: str = Query(...)):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        doc = session.execute(
            select(Doctors)
                .where(Doctors.id == doc_id)
        ).schalars().first()
        schedule = session.execute(
            select(MedicalSchedules)
                .where(MedicalSchedules.id == schedule_id)
        ).schalars().first()

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
            )
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doc_id} not found")

locations = APIRouter(
    prefix="/locations",
    tags=["locations"],
    dependencies=[
        Depends(auth)
    ]
)

@doctors.put("/ban/{doc_id}/", response_model=DoctorResponse)
async def ban_doc(request: Request, doc_id: str, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doc_id)
    doc: Doctors = session.execute(statement).scalars().first()

    doc.is_banned = True
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
        ),
        "message":f"User {doc.name} has been banned."
    })

@doctors.put("/unban/{doc_id}/", response_model=DoctorResponse)
async def unban_doc(request: Request, doc_id: str, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    statement = select(Doctors).where(Doctors.id == doc_id)
    doc: Doctors = session.execute(statement).scalars().first()

    doc.is_banned = False
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
        ),
        "message":f"User {doc.name} has been unbanned."
    })

@locations.get("/", response_model=List[LocationResponse])
async def get_locations(request: Request, session: SessionDep):
    statement = select(Locations)
    result = session.execute(statement).scalars().all()
    locations: List["LocationResponse"] = []
    for location in result:
        statement = select(Departments).where(Departments.location_id == location.id)
        result: List["Departments"] = session.execute(statement).scalars().all()
        departments = []
        for department in result:
            statement = select(Specialties).where(Specialties.department_id == department.id)
            result: List["Specialties"] = session.execute(statement).scalars().all()
            specialties = []
            for specialty in result:
                statement = select(Services).where(Services.specialty_id == specialty.id)
                result: List["Services"] = session.execute(statement).scalars().all()
                services: List["ServiceResponse"] = []
                for service in result:
                    services.append(
                        ServiceResponse(
                            id=service.id,
                            name=service.name,
                            description=service.description,
                            price=service.price,
                            specialty_id=service.specialty_id
                        )
                    )
                statement = select(Doctors).where(Doctors.service_id == specialty.id)
                result: List["Doctors"] = session.execute(statement).scalars().all()
                doctors = []
                for doc in result:
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
                        )
                    )
                specialties.append(
                    SpecialtyResponse(
                        id=specialty.id,
                        name=specialty.name,
                        description=specialty.description,
                        department_id=specialty.department_id,
                        services=services,
                        doctors=doctors
                    )
                )
            departments.append(
                DepartmentResponse(
                    id=department.id,
                    name=department.name,
                    description=department.description,
                    location_id=department.location_id,
                    specialities=specialties
                )
            )
        locations.append(
            LocationResponse(
                id=location.id,
                name=location.name,
                description=location.description,
                departments=departments
            )
        )

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
                name=new_location.name
            ).model_dump(),
            status_code=status.HTTP_201_CREATED
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@locations.delete("/delete/{location_id}", response_model=LocationDelete)
async def delete_location(request: Request, location_id: int, session: SessionDep):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    location: Locations = session.execute(
        select(Locations)
            .where(Locations.id == location_id)
    ).scalars().first()

    session.delete(location)
    session.commit()

    return ORJSONResponse(
        LocationDelete(
            id=location.id,
            message=f"Location {location.name} deleted"
        ).model_dump()
    )

@locations.put("/update/{location_id}/", response_model=LocationResponse)
async def update_location(request: Request, location_id: int, session: SessionDep, location: LocationUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    new_location = session.execute(
        select(Locations)
            .where(Locations.id == location_id)
    ).scalars().first()

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
    statement = select(Services)
    result: List["Services"] = session.execute(statement).scalars().all()
    services = []
    for service in result:
        services.append(
            ServiceResponse(
                id=service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id
            )
        )

    return ORJSONResponse(services)

@services.post("/add/", response_model=ServiceResponse)
async def set_service(request: Request, session: SessionDep, service: ServiceCreate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    try:
        new_service = Services(
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id
        )

        session.add(new_service)
        session.commit()
        session.refresh(new_service)

        return ORJSONResponse(
            ServiceResponse(
                id=service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id
            )
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        return ORJSONResponse({
            "error": str(e),
        }, status_code=status.HTTP_400_BAD_REQUEST)

@services.delete("/delete/{service_id}/", response_model=ServiceDelete)
async def delete_service(request: Request, session: SessionDep, service_id :str):
    try:
        service = session.execute(select(Services).where(Services.id == service_id)).scalars().first()

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

@services.put("/update/{service_id}/", response_model=ServiceResponse)
async def update_service(request: Request, session: SessionDep, service_id: str, service: ServiceUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    new_service: Services = session.execute(
        select(Services)
            .where(Services.id == service_id)
    ).scalars().first()

    fields = service._fields_.keys()

    for field in fields:
        value = getattr(service, field)
        if value is None:
            continue
        setattr(new_service, field, value)

    session.add(new_service)
    session.commit()

    return ORJSONResponse(
        ServiceResponse(
            id=new_service.id,
            name=new_service.name,
            description=new_service.description,
        ).model_dump()
    )



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
    result: List["Specialties"] = session.execute(statement).scalars().all()

    specialities: List[SpecialtyResponse] = []
    for specialiti in result:
        statement = select(Services).where(Services.specialty_id == specialiti.id)
        result: List["Services"] = session.execute(statement).scalars().all()

        services: List[ServiceResponse] = []
        for service in result:
            services.append(
                ServiceResponse(
                    id=service.id,
                    name=service.name,
                    description=service.description,
                    price=service.price,
                    specialty_id=service.specialty_id
                )
            )

        statement = select(Doctors).where(Doctors.speciality_id == specialiti.id)
        result: List["Doctors"] = session.execute(statement).scalars().all()

        doctors: List[DoctorResponse] = []
        for doc in result:
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
                )
            )

        specialities.append(
            SpecialtyResponse(
                id=specialiti.id,
                name=specialiti.name,
                description=specialiti.description,
                department_id=specialiti.department_id,
                doctors=doctors,
                services=services
            )
        )

    return ORJSONResponse(
        specialities,
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


@specialities.delete("/delete/{speciality_id}}/", response_model=SpecialtyDelete)
async def delete_speciality(request: Request, session: SessionDep, speciality_id: str):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    speciality: Specialties = session.excecute(
        select(Specialties)
            .where(Specialties.id == speciality_id)
    ).scalars().first()

    session.delete(speciality)
    session.commt()

    return ORJSONResponse(
        SpecialtyDelete(
            id=speciality.id,
            message=f"Specialty {speciality.name} has been deleted"
        ).model_dump()
    )

@specialities.put("/update/{speciality_id}/", response_model=SpecialtyResponse)
async def update_speciality(request: Request, session: SessionDep, speciality_id: str, speciality: SpecialtyUpdate):

    if not request.state.user.is_superuser:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="scopes have not unauthorized")

    new_speciality: Services = session.execute(
        select(Specialties).where(Specialties.id == speciality_id)
    ).scalers().first()

    fields = speciality._fields_.keys()
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
    tags=["chat"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, WebSocket] = {}  # user_id → WebSocket

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()  # Handshake HTTP→WS :contentReference[oaicite:4]{index=4}
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: UUID):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: UUID):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)  # envía JSON → cliente :contentReference[oaicite:5]{index=5}

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

    def is_connected(self, doc_id) -> bool:
        return doc_id in self.active_connections


manager = ConnectionManager()

@chat.get("/", response_model=List[ChatResponse])
async def get_chats(request: Request, session: SessionDep):
    try:
        chats: List[Chat] = session.excetute(
            select(Chat)
        ).scalars().all()

        chats_list: List["ChatResponse"] = []
        for chat_i in chats:
            doctor_1: Doctors = session.execute(
                select(Doctors).where(Doctors.id == chat_i.doc_1_id)
            )
            doctor_2: Doctors = session.execute(
                select(Doctors).where(Doctors.id == chat_i.doc_2_id)
            )

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
async def create_chat(request: Request, session: SessionDep, doc_2_id = Query(...)):
    if not "doc" in request.state.scopes:
        raise HTTPException(status_code=401, detail="Unauthorized")

    doc: Doctors = request.state.user

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

@chat.websocket("/ws/chat/{chat_id}")
async def websocket_chat(request: Request, websocket: WebSocket, session: SessionDep, chat_id):
    if not "doc" in request.state.scopes:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        doc: Doctors = request.state.user

        if isinstance(doc, User):
            raise HTTPException(status_code=403, detail="You are not authorized")

        chat: Chat = session.execute(select(Chat).where(Chat.id == chat_id))
        print(chat)
        if chat.doc_1_id == doc.id or chat.doc_2_id == doc.id:
            await websocket.close(1008)
    except Exception:
        console.print_exception(show_locals=True)
        await websocket.close(1008)
    if isinstance(doc, User):
        await websocket.close(1008)
        return
    await manager.connect(doc.id, websocket)
    try:
        await manager.broadcast({"type":"presence","user":doc.id,"status":"offline"})
        while True:
            data = await websocket.receive_json()
            content = data["content"]

            chat: Chat = session.execute(select(Chat).where(Chat.id == chat_id))

            message = ChatMessages(
                sender_id=doc.id,
                chat_id=chat_id,
                content=content,
                chat=chat,
            )

            session.add(message)
            session.commit()
            session.refresh(message)

            if manager.is_connected(doc.id):
                await websocket.send_json({
                    "type":"message",
                    "message":message.model_dump(mode="json")
                })

    except WebSocketDisconnect:
        manager.disconnect(doc.id)
        await manager.broadcast({"type":"presence","user":doc.id,"status":"offline"})



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