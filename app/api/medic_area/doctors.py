"""Doctor related routes."""
from typing import Annotated, List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import ORJSONResponse
from sqlmodel import select

from app.db.main import SessionDep
from app.models import DoctorStates as DoctorStateModel
from app.models import Doctors, MedicalSchedules, User
from app.schemas import UserRead
from app.schemas.medica_area import (
    DoctorCreate,
    DoctorDelete,
    DoctorPasswordUpdate,
    DoctorResponse,
    DoctorSpecialityUpdate,
    DoctorUpdate,
    MedicalScheduleResponse,
)
from app.core.interfaces.medic_area import DoctorRepository

from .common import auth_dependency, console, default_response_class


router = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@router.get("/", response_model=List[DoctorResponse])
async def get_doctors(session: SessionDep):
    result = session.exec(select(Doctors).where(True)).all()
    doctors_serialized = [
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
            doctor_state=doc.doctor_state,
            address=doc.address,
        ).model_dump()
        for doc in result
    ]

    return ORJSONResponse(doctors_serialized)


@router.get("/{doctor_id}/", response_model=DoctorResponse)
async def get_doctor_by_id(doctor_id: UUID, session: SessionDep):
    doc = session.get(Doctors, doctor_id)

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
                )
                for schedule in doc.medical_schedules
            ],
        ).model_dump()
    )


@router.get("/me", response_model=DoctorResponse)
async def me_doctor(request: Request, session: SessionDep):
    doc: Doctors | User = request.state.user

    if isinstance(doc, User):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    doc = session.merge(doc)
    session.refresh(doc)

    return ORJSONResponse(
        {
            "doc": DoctorResponse(
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
                    )
                    for schedule in doc.medical_schedules
                ],
            ).model_dump()
        }
    )


@router.get("/{doctor_id}/patients", response_model=List[UserRead])
async def get_patients_by_doctor(
    request: Request, doctor_id: UUID, session: SessionDep
):
    try:
        doc = session.get(Doctors, doctor_id)
        users_list = [appointment.user for appointment in doc.appointments]

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
                    img_profile=user.url_image_profile,
                ).model_dump()
                for user in users_list
            ],
            status_code=status.HTTP_200_OK,
        )

    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/{doctor_id}/stats")
async def get_doctor_stats_by_id(
    request: Request, doctor_id: str, session: SessionDep
):
    try:
        doctor = await DoctorRepository.get_doctor_by_id(session, UUID(doctor_id))
        metrics = await DoctorRepository.get_doctor_metrics(session, doctor)

        return ORJSONResponse(metrics, status_code=status.HTTP_200_OK)
    except Exception as exc:  # pragma: no cover - mirrors previous behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.post("/add/", response_model=DoctorResponse)
async def add_doctor(request: Request, doctor: DoctorCreate, session: SessionDep):
    try:
        user: User = request.state.user

        if not user.is_superuser and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
            )

        new_doctor = Doctors(
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
            doctor_state=doctor.doctor_state,
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
                speciality_id=new_doctor.speciality_id,
                address=new_doctor.address,
                blood_type=new_doctor.blood_type,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:  # pragma: no cover - mirrors existing behaviour
        console.print_exception(show_locals=True)
        return ORJSONResponse({"error": str(exc)}, status_code=status.HTTP_400_BAD_REQUEST)


@router.delete("/delete/{doctor_id}/", response_model=DoctorDelete)
async def delete_doctor(request: Request, doctor_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    statement = select(Doctors).where(Doctors.id == doctor_id)
    result = session.exec(statement).first()
    if result:
        session.delete(result)
        session.commit()

        return ORJSONResponse(
            DoctorDelete(
                id=result.id,
                message=f"Doctor {doctor_id} deleted",
            ).model_dump()
        )
    return ORJSONResponse({"error": "Doctor not found"}, status_code=404)


@router.delete(
    "/delete/{doctor_id}/schedule/{schedule_id}/",
    response_model=DoctorResponse,
)
async def delete_doctor_schedule_by_id(
    request: Request, schedule_id: UUID, doctor_id: UUID, session: SessionDep
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    doc = session.exec(select(Doctors).where(Doctors.id == doctor_id)).first()

    doc.medical_schedules = [i for i in doc.medical_schedules if i.id != schedule_id]

    session.add(doc)
    session.commit()

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
        ).model_dump()
    )


@router.patch("/update/{doctor_id}/", response_model=DoctorUpdate)
async def update_doctor(
    request: Request,
    doctor_id: UUID,
    session: SessionDep,
    doctor: Annotated[DoctorUpdate, Form(...)],
):
    if "doc" not in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    if request.state.user.id != doctor_id and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not un unauthorized",
        )

    try:
        doc = session.exec(select(Doctors).where(Doctors.id == doctor_id)).first()

        form_fields = doctor.__fields__.keys()
        actor = getattr(request.state, "user", None)
        actor_id = getattr(actor, "id", None)

        for field in form_fields:
            value = getattr(doctor, field, None)
            console.print(field, " = ", value)
            if field == "doctor_state":
                if value in [None, "", " "]:
                    continue
                try:
                    state_enum = DoctorStateModel(value)
                    doc.update_state(state_enum, actor_id=actor_id)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid doctor state provided",
                    ) from exc
            elif field == "username" and value not in [None, "", " "]:
                doc.name = value
            elif (
                value is not None
                and field not in ["username", "doctor_state"]
                and value not in ["", " "]
            ):
                setattr(doc, field, value)

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
                address=doc.address,
                doctor_state=doc.doctor_state,
            ).model_dump()
        )

    except Exception as exc:  # pragma: no cover - existing behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=404, detail=f"Doctor {doctor_id} not found"
        ) from exc


@router.patch("/update/{doctor_id}/speciality", response_model=DoctorResponse)
async def update_speciality(
    request: Request,
    doctor_id: UUID,
    session: SessionDep,
    doctor_form: Annotated[DoctorSpecialityUpdate, Form(...)],
):
    if "doc" not in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not un un unauthorized",
        )

    if request.state.user.id != doctor_id and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not un un unauthorized",
        )

    try:
        doc = session.exec(select(Doctors).where(Doctors.id == doctor_id)).first()

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
                speciality_id=doc.speciality_id,
            ).model_dump()
        )

    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=404, detail=f"Doctor {doctor_id} not found"
        ) from exc


@router.patch("/update/{doctor_id}/password")
async def update_doctor_password(
    request: Request,
    doctor_id: UUID,
    session: SessionDep,
    password: Annotated[DoctorPasswordUpdate, Form()],
):
    if "doc" not in request.state.scopes and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    if request.state.user.id != doctor_id and not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not un unauthorized",
        )

    try:
        doc = session.exec(select(Doctors).where(Doctors.id == doctor_id)).first()

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
                speciality_id=doc.speciality_id,
            ).model_dump()
        )

    except Exception as exc:  # pragma: no cover - existing behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=404, detail=f"Doctor {doctor_id} not found"
        ) from exc


@router.patch("/add/schedule/", response_model=DoctorResponse)
async def add_schedule_by_id(
    request: Request,
    session: SessionDep,
    schedule_id: UUID = Query(...),
    doc_id: UUID = Query(...),
):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    try:
        doc = session.exec(select(Doctors).where(Doctors.id == doc_id)).first()
        schedule = session.exec(
            select(MedicalSchedules).where(MedicalSchedules.id == schedule_id)
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
                speciality_id=doc.speciality_id,
            ).model_dump()
        )
    except Exception as exc:  # pragma: no cover - mirrors behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=404, detail=f"Doctor {doc_id} not found"
        ) from exc


@router.patch("/ban/{doc_id}/", response_model=DoctorResponse)
async def ban_doc(request: Request, doc_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    doc = session.exec(select(Doctors).where(Doctors.id == doc_id)).first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Doctor {doc_id} not found")

    actor = getattr(request.state, "user", None)
    actor_id = getattr(actor, "id", None)

    try:
        doc.deactivate(actor_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.add(doc)
    session.commit()
    session.refresh(doc)

    return ORJSONResponse(
        {
            "doc": DoctorResponse(
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
            ).model_dump(),
            "message": f"Doctor {doc.name} has been banned.",
        }
    )


@router.patch("/unban/{doc_id}/", response_model=DoctorResponse)
async def unban_doc(request: Request, doc_id: UUID, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="scopes have not unauthorized",
        )

    doc = session.exec(select(Doctors).where(Doctors.id == doc_id)).first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Doctor {doc_id} not found")

    actor = getattr(request.state, "user", None)
    actor_id = getattr(actor, "id", None)

    try:
        doc.activate(actor_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.add(doc)
    session.commit()
    session.refresh(doc)

    return ORJSONResponse(
        {
            "doc": DoctorResponse(
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
            ).model_dump(),
            "message": f"Doctor {doc.name} has been unbanned.",
        }
    )


__all__ = ["router"]
