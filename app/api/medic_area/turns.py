"""Turn management routes."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse, Response
from sqlalchemy.orm import selectinload
from sqlmodel import select

import os

from app.db.main import SessionDep
from app.models import (
    Appointments,
    Departments,
    Doctors,
    Services,
    Specialties,
    TurnDocument,
    TurnDocumentDownload,
    Turns,
    User,
)
from app.schemas.medica_area import (
    AppointmentResponse,
    DepartmentResponse,
    DoctorResponse,
    PayTurnResponse,
    ServiceResponse,
    SpecialtyResponse,
    TurnDocumentDownloadLog,
    TurnDocumentSummary,
    TurnReschedule,
    TurnsCreate,
    TurnsDelete,
    TurnsResponse,
    TurnsState,
)
from app.core.interfaces.medic_area import TurnAndAppointmentRepository
from app.core.services.pdf import (
    get_or_create_turn_document,
    register_turn_document_download,
)
from app.core.services.stripe_payment import StripeServices
from app.audit import (
    AuditAction,
    AuditEmitter,
    AuditEventCreate,
    AuditSeverity,
    AuditTargetType,
    build_request_metadata,
    get_audit_emitter,
    get_request_identifier,
)

from .common import auth_dependency, console, default_response_class


router = APIRouter(
    prefix="/turns",
    tags=["turns"],
    default_response_class=default_response_class,
    dependencies=[auth_dependency()],
)


@dataclass(frozen=True)
class TurnAccessContext:
    """Contextual information about a user's relationship with a turn."""

    is_superuser: bool
    is_owner: bool
    is_assigned_doctor: bool
    has_doctor_scope: bool


def get_turn_with_relations(
    *,
    session: SessionDep,
    turn_id: UUID,
    request_user: User,
    scopes: Iterable[str] | None = None,
) -> tuple[Turns, TurnAccessContext]:
    """Retrieve a turn with related entities and evaluate user access."""

    statement = (
        select(Turns)
        .where(Turns.id == turn_id)
        .options(
            selectinload(Turns.user),
            selectinload(Turns.doctor)
            .selectinload(Doctors.speciality)
            .selectinload(Specialties.departament),
            selectinload(Turns.services)
            .selectinload(Services.speciality)
            .selectinload(Specialties.departament),
        )
    )

    turn = session.exec(statement).first()

    if turn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turn not found",
        )

    scope_set = set(scopes or [])
    access_context = TurnAccessContext(
        is_superuser=getattr(request_user, "is_superuser", False),
        is_owner=turn.user_id == getattr(request_user, "id", None),
        is_assigned_doctor=turn.doctor_id == getattr(request_user, "id", None),
        has_doctor_scope="doc" in scope_set,
    )

    return turn, access_context


def _has_turn_document_access(access: TurnAccessContext) -> bool:
    """Evaluate if the current context grants access to turn documents."""

    return (
        access.is_superuser
        or (access.has_doctor_scope and access.is_assigned_doctor)
        or (not access.has_doctor_scope and access.is_owner)
    )


async def _serve_turn_document_response(
    request: Request,
    session: SessionDep,
    *,
    turn: Turns,
    access: TurnAccessContext,
    emitter: AuditEmitter,
) -> Response:
    """Generate (or reuse) a PDF for a turn and return it as a response."""

    request_user = request.state.user

    if not _has_turn_document_access(access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized")

    document, pdf_bytes, created = get_or_create_turn_document(session, turn)

    if created:
        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.TURN_DOCUMENT_GENERATED,
                actor_id=getattr(request_user, "id", None),
                target_id=document.id,
                target_type=AuditTargetType.TURN_DOCUMENT,
                details={
                    "turn_id": str(turn.id),
                    "file_path": document.file_path,
                },
            )
        )

    download = register_turn_document_download(
        session,
        document=document,
        user_id=getattr(request_user, "id", document.user_id),
        channel=request.headers.get("x-download-channel", "api"),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await emitter.emit_event(
        _make_event(
            request,
            action=AuditAction.TURN_DOCUMENT_DOWNLOADED,
            actor_id=getattr(request_user, "id", None),
            target_id=document.id,
            target_type=AuditTargetType.TURN_DOCUMENT,
            details={
                "turn_id": str(turn.id),
                "download_id": str(download.id),
                "channel": download.channel,
                "client_ip": download.client_ip,
            },
        )
    )

    filename = Path(document.file_path).name

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


def _serialize_doctor(doctor: Doctors | None) -> dict | None:
    if doctor is None:
        return None

    return DoctorResponse(
        id=doctor.id,
        dni=doctor.dni,
        username=doctor.name,
        speciality_id=doctor.speciality_id,
        date_joined=doctor.date_joined,
        is_active=doctor.is_active,
        email=doctor.email,
        first_name=doctor.first_name,
        last_name=doctor.last_name,
        telephone=doctor.telephone,
    ).model_dump()


def _serialize_services(services: Iterable[Services]) -> list[dict]:
    return [
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
        ).model_dump()
        for service in services
    ]


def _serialize_turn(turn: Turns | None) -> dict | None:
    if turn is None:
        return None

    return TurnsResponse(
        id=turn.id,
        reason=turn.reason,
        state=turn.state,
        date=turn.date,
        date_limit=turn.date_limit,
        date_created=turn.date_created,
        user_id=turn.user_id,
        doctor_id=turn.doctor_id,
        time=turn.time,
        service=_serialize_services(turn.services),
        doctor=_serialize_doctor(turn.doctor),
    ).model_dump()


def _make_event(
    request: Request,
    *,
    action: AuditAction,
    severity: AuditSeverity = AuditSeverity.INFO,
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
    target_type: AuditTargetType = AuditTargetType.APPOINTMENT,
    details: dict | None = None,
) -> AuditEventCreate:
    return AuditEventCreate(
        action=action,
        severity=severity,
        target_type=target_type,
        actor_id=actor_id,
        target_id=target_id,
        request_id=get_request_identifier(request),
        request_metadata=build_request_metadata(request),
        details=dict(details or {}),
    )


@router.get("/", response_model=List[TurnsResponse])
async def get_turns(request: Request, session: SessionDep):
    if not request.state.user.is_superuser:
        raise HTTPException(status_code=401, detail="You are not authorized")

    statement = select(Turns)
    result = session.exec(statement).all()

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
                service=[
                    ServiceResponse(
                        id=serv.id,
                        name=serv.name,
                        description=serv.description,
                        price=serv.price,
                        specialty_id=serv.specialty_id,
                    )
                    for serv in turn.services
                ],
            ).model_dump()
        )

    return ORJSONResponse(turns_serialized)


Serializer = TypeVar("Serializer")


def serialize_model(
    model: object, serializer: Serializer, session, refresh: bool = False
) -> Serializer:
    """Helper to copy fields from a model into a serializer instance."""
    fields = serializer.__fields__.keys()
    serializer_instance = serializer()
    for field in fields:
        setattr(serializer_instance, field, getattr(model, field))

    if refresh:
        session.refresh(model)

    return serializer_instance


@router.get("/user/pdf/{user_id}/{turn_id}")
async def get_turn_data_pdf(
    request: Request,
    session: SessionDep,
    user_id: UUID,
    turn_id: UUID,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """Endpoint to get turn data in PDF format."""

    request_user = request.state.user

    if not request_user.is_superuser and user_id != request_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to inspect other users turns",
        )

    try:
        turn, access = get_turn_with_relations(
            session=session,
            turn_id=turn_id,
            request_user=request_user,
            scopes=getattr(request.state, "scopes", []) or [],
        )

        return await _serve_turn_document_response(
            request,
            session,
            turn=turn,
            access=access,
            emitter=emitter,
        )

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - preserve behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the PDF",
        ) from exc


@router.get("/{turn_id}/pdf")
async def download_turn_pdf(
    request: Request,
    session: SessionDep,
    turn_id: UUID,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    """Download the authenticated user's PDF receipt for a given turn."""

    request_user: User | None = getattr(request.state, "user", None)

    if request_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized")

    try:
        turn, access = get_turn_with_relations(
            session=session,
            turn_id=turn_id,
            request_user=request_user,
            scopes=getattr(request.state, "scopes", []) or [],
        )

        return await _serve_turn_document_response(
            request,
            session,
            turn=turn,
            access=access,
            emitter=emitter,
        )

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - maintain behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the PDF",
        ) from exc


@router.get("/documents/me", response_model=List[TurnDocumentSummary])
async def list_my_turn_documents(request: Request, session: SessionDep):
    """List PDF turn documents generated for the authenticated user."""

    request_user: User | None = getattr(request.state, "user", None)

    if request_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized")

    try:
        statement = (
            select(TurnDocument)
            .where(TurnDocument.user_id == request_user.id)
            .options(
                selectinload(TurnDocument.turn)
                .selectinload(Turns.doctor)
                .selectinload(Doctors.speciality)
                .selectinload(Specialties.departament),
                selectinload(TurnDocument.turn)
                .selectinload(Turns.services)
                .selectinload(Services.speciality)
                .selectinload(Specialties.departament),
            )
            .order_by(TurnDocument.generated_at.desc())
        )

        documents = session.exec(statement).all()

        payload = [
            TurnDocumentSummary(
                id=document.id,
                turn_id=document.turn_id,
                user_id=document.user_id,
                file_path=document.file_path,
                generated_at=document.generated_at,
                turn=_serialize_turn(document.turn),
            ).model_dump()
            for document in documents
        ]

        return ORJSONResponse(payload)
    except Exception as exc:  # pragma: no cover - keep behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve turn documents",
        ) from exc


@router.get(
    "/documents/me/downloads",
    response_model=List[TurnDocumentDownloadLog],
)
async def list_my_turn_document_downloads(request: Request, session: SessionDep):
    """Optionally expose the authenticated user's download history."""

    request_user: User | None = getattr(request.state, "user", None)

    if request_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized")

    try:
        statement = (
            select(TurnDocumentDownload)
            .where(TurnDocumentDownload.user_id == request_user.id)
            .options(
                selectinload(TurnDocumentDownload.turn)
                .selectinload(Turns.doctor)
                .selectinload(Doctors.speciality)
                .selectinload(Specialties.departament),
                selectinload(TurnDocumentDownload.turn)
                .selectinload(Turns.services)
                .selectinload(Services.speciality)
                .selectinload(Specialties.departament),
            )
            .order_by(TurnDocumentDownload.downloaded_at.desc())
        )

        downloads = session.exec(statement).all()

        payload = [
            TurnDocumentDownloadLog(
                id=download.id,
                turn_document_id=download.turn_document_id,
                turn_id=download.turn_id,
                user_id=download.user_id,
                downloaded_at=download.downloaded_at,
                channel=download.channel,
                client_ip=download.client_ip,
                user_agent=download.user_agent,
                turn=_serialize_turn(download.turn),
            ).model_dump()
            for download in downloads
        ]

        return ORJSONResponse(payload)
    except Exception as exc:  # pragma: no cover - mirror behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve download history",
        ) from exc


@router.get("/user/{user_id}", response_model=Optional[List[TurnsResponse]])
async def get_turns_by_user_id(
    request: Request, session: SessionDep, user_id: UUID
):
    request_user: User | None = getattr(request.state, "user", None)

    if request_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not authorized")

    if not request_user.is_superuser and user_id != request_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to inspect other users turns",
        )

    load_options = (
        selectinload(User.turns),
        selectinload(User.turns)
        .selectinload(Turns.doctor)
        .selectinload(Doctors.speciality)
        .selectinload(Specialties.departament),
        selectinload(User.turns)
        .selectinload(Turns.services)
        .selectinload(Services.speciality)
        .selectinload(Specialties.departament),
    )

    def _load_user_with_turns(target_user_id: UUID) -> User | None:
        statement = select(User).where(User.id == target_user_id).options(*load_options)
        return session.exec(statement).first()

    db_request_user = _load_user_with_turns(request_user.id)

    if db_request_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user not found",
        )

    if request_user.is_superuser and user_id != request_user.id:
        target_user = _load_user_with_turns(user_id)
    else:
        target_user = db_request_user

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    def serialize_departament(department: Departments):
        if department is None:
            return None
        return DepartmentResponse(
            id=department.id,
            name=department.name,
            description=department.description,
            location_id=department.location_id,
        )

    def serialize_speciality(speciality: Specialties):
        if speciality is None:
            return None
        return SpecialtyResponse(
            id=speciality.id,
            name=speciality.name,
            description=speciality.description,
            department_id=speciality.department_id,
            department=serialize_departament(speciality.departament),
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
                doctor=(
                    DoctorResponse(
                        id=turn.doctor.id,
                        dni=turn.doctor.dni,
                        username=turn.doctor.name,
                        speciality_id=turn.doctor.speciality_id,
                        date_joined=turn.doctor.date_joined,
                        is_active=turn.doctor.is_active,
                        email=turn.doctor.email,
                        first_name=turn.doctor.first_name,
                        last_name=turn.doctor.last_name,
                        telephone=turn.doctor.telephone,
                    ).model_dump()
                    if turn.doctor
                    else None
                ),
                service=[
                    ServiceResponse(
                        id=service.id,
                        name=service.name,
                        description=service.description,
                        price=service.price,
                        specialty_id=service.specialty_id,
                    ).model_dump()
                    for service in turn.services
                ],
            ).model_dump()
            for turn in target_user.turns
        ]

        return ORJSONResponse(turns_serialized, status_code=200)
    except Exception as exc:  # pragma: no cover - mirrors behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/{turn_id}", response_model=TurnsResponse)
async def get_turn_by_id(request: Request, session: SessionDep, turn_id: UUID):
    user = request.state.user

    try:
        turn, access = get_turn_with_relations(
            session=session,
            turn_id=turn_id,
            request_user=user,
            scopes=getattr(request.state, "scopes", []) or [],
        )

        if not (access.is_superuser or access.is_owner or access.is_assigned_doctor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You don't have permission to access this turn"
            )

        return ORJSONResponse(
            TurnsResponse(
                id=turn.id,
                reason=turn.reason,
                state=turn.state,
                date=turn.date,
                date_limit=turn.date_limit,
                date_created=turn.date_created,
                user_id=turn.user_id,
                doctor_id=turn.doctor_id,
                time=turn.time,
                # Incluir servicios si están disponibles
                service=[
                    ServiceResponse(
                        id=service.id,
                        name=service.name,
                        description=service.description,
                        price=service.price,
                        specialty_id=service.specialty_id,
                    ).model_dump()
                    for service in turn.services
                ] if turn.services else []
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exc)
        ) from exc


@router.post("/add", response_model=PayTurnResponse)
async def create_turn(request: Request, session: SessionDep, turn: TurnsCreate):
    user: User | None = request.state.user

    if "doc" in request.state.scopes:
        if turn.user_id is None:
            raise HTTPException(status_code=400, detail="user_id is required")

    elif user:
        turn.user_id = user.id

    else:
        raise HTTPException(status_code=500, detail="Internal Error")

    try:
        new_turn, new_appointment = await TurnAndAppointmentRepository.create_turn_and_appointment(
            session=session,
            turn=turn,
        )

        if not new_turn:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=new_appointment)

        response = await StripeServices.proces_payment(
            price=new_turn.price_total(),
            details=new_turn.get_details(),
            h_i=turn.health_insurance,
            session=session,
        )

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
                    time=new_turn.time,
                ).model_dump(),
                payment_url=response,
            ).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )

    except HTTPException as exc:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    except Exception as exc:  # pragma: no cover - keep behaviour
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{turn_id}/reschedule", response_model=TurnsResponse)
async def reschedule_turn(
    request: Request,
    session: SessionDep,
    turn_id: UUID,
    payload: TurnReschedule,
):
    user = getattr(request.state, "user", None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized"
        )

    scopes = getattr(request.state, "scopes", []) or []
    turn, access = get_turn_with_relations(
        session=session,
        turn_id=turn_id,
        request_user=user,
        scopes=scopes,
    )

    # Superusers pueden reprogramar cualquier turno
    # Doctores solo pueden reprogramar sus propios turnos
    # Pacientes solo pueden reprogramar sus propios turnos
    is_authorized = (
        access.is_superuser
        or (access.has_doctor_scope and access.is_assigned_doctor)
        or (not access.has_doctor_scope and access.is_owner)
    )

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You are not authorized to reschedule this turn"
        )

    try:
        updated_turn = await TurnAndAppointmentRepository.reschedule_turn(
            session=session,
            turn=turn,
            date=payload.date,
            time=payload.time,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - preserve logging behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(exc)
        ) from exc

    session.refresh(updated_turn)

    services = [
        ServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            specialty_id=service.specialty_id,
        ).model_dump()
        for service in updated_turn.services
    ]

    return ORJSONResponse(
        TurnsResponse(
            id=updated_turn.id,
            reason=updated_turn.reason,
            state=updated_turn.state,
            date=updated_turn.date,
            date_limit=updated_turn.date_limit,
            date_created=updated_turn.date_created,
            user_id=updated_turn.user_id,
            doctor_id=updated_turn.doctor_id,
            appointment_id=str(updated_turn.appointment.id)
            if updated_turn.appointment
            else None,
            time=updated_turn.time,
            service=services,
        ).model_dump()
    )

@router.delete("/delete/{turn_id}", response_model=TurnsDelete)
async def delete_turn(
    request: Request,
    session: SessionDep,
    turn_id: UUID,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    session_user = request.state.user
    try:
        turn, access = get_turn_with_relations(
            session=session,
            turn_id=turn_id,
            request_user=session_user,
            scopes=getattr(request.state, "scopes", []) or [],
        )
        is_authorized = (
            access.is_superuser
            or (access.has_doctor_scope and access.is_assigned_doctor)
            or (not access.has_doctor_scope and access.is_owner)
        )

        if not is_authorized:
            raise HTTPException(status_code=403, detail="You are not authorized")
        deleted = TurnAndAppointmentRepository.delete_turn_and_appointment(session, turn)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"the turn: {turn_id} cannot be deleted",
            )
        response = ORJSONResponse(
            TurnsDelete(
                id=turn.id,
                message=f"Turn {turn.id} has been deleted",
            ),
            status_code=status.HTTP_200_OK,
        )

        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.RECORD_DELETED,
                severity=AuditSeverity.WARNING,
                actor_id=getattr(session_user, "id", None),
                target_id=turn.id,
                details={"entity": "Turn", "appointment_id": str(turn.appointment.id) if turn.appointment else None},
            )
        )

        return response
    except Exception as exc:  # pragma: no cover - preserve behaviour
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/update/state")
async def update_state(
    request: Request,
    turn_id: UUID,
    new_state: str,
    session: SessionDep,
    emitter: AuditEmitter = Depends(get_audit_emitter),
):
    turn = session.get(Turns, turn_id)

    if not turn:
        raise HTTPException(404, detail="Turn Not Found")

    if "superuser" not in request.state.scopes:
        if turn.state.value in ["finished", "rejected", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Turn has a not mutable state",
            )

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
                raise HTTPException(
                    status.HTTP_501_NOT_IMPLEMENTED,
                    detail=f"{new_state} isn´t in the valid states",
                )

        session.add(turn)
        session.commit()

        await emitter.emit_event(
            _make_event(
                request,
                action=AuditAction.APPOINTMENT_STATE_UPDATED,
                actor_id=getattr(request.state.user, "id", None),
                target_id=turn.id,
                details={"new_state": turn.state.value},
            )
        )

        return ORJSONResponse({"msg": "success"}, status_code=200)

    except HTTPException:
        raise

    except Exception as exc:  # pragma: no cover - retain behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(500, detail=str(exc)) from exc


__all__ = ["router"]
