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

from app.models.users import User
from app.models.medic_area import (
    Doctors,
    MedicalSchedules,
    Locations,
    Services,
    Specialties,
    Departments,
    ChatMessages,
    Chat
)
from app.schemas.medica_area import (
    MedicalScheduleCreate,
    MedicalScheduleDelete,
    MedicalScheduleUpdate,
    MedicalScheduleResponse
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
    LocationUpdate,
)
from app.schemas.medica_area import (
    DepartmentResponse
)
from app.schemas.medica_area import (
    SpecialtyResponse,
    ServiceCreate,
    ServiceDelete,
    SpecialtyUpdate
)
from app.schemas.medica_area import (
    ServiceResponse,
    ServiceCreate,
    ServiceDelete,
    ServiceUpdate,
)
from app.db.main import SessionDep
from app.core.auth import JWTBearer, JWTWebSocket

auth = JWTBearer(auto_error=False)
ws_auth = JWTWebSocket()

console = Console()

schedules = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    default_response_class=ORJSONResponse,
)

@schedules.get("/", response_model=List[MedicalScheduleResponse])
async def get_medical_schedules(request: Request, session: SessionDep):
    statement = select(MedicalSchedules)
    result: List[MedicalSchedules] = session.execute(statement).scalars().all()
    schedules = []
    for schedule_i in result:
        doctors: List[DoctorResponse] = []
        for doctor_i in schedule_i.doctors:
            doctor = DoctorResponse(
                id=doctor_i.id,
                name=doctor_i.name,
                lastname=doctor_i.lastname,
                dni=doctor_i.dni,
                telephone=doctor_i.telephone,
                email=doctor_i.email,
                speciality_id=doctor_i.speciality_id
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
async def add_schedule(request: Request, medical_schedule: MedicalScheduleCreate, session: SessionDep):
    schedule = MedicalSchedules(
        day=medical_schedule.day,
        time_medic=medical_schedule.time_medic,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return ORJSONResponse(
        MedicalScheduleResponse(
            id=schedule.id,
            day=schedule.day,
            time_medic=schedule.time_medic,
            doctors=schedule.doctors
        ).model_dump(),
        status_code=status.HTTP_201_CREATED
    )

@schedules.post("/add/doctor/", response_model=MedicalScheduleResponse)
async def add_doctor_by_id(request: Request, session: SessionDep, doc_id: str = Query(...), schedule_id: str = Query(...)):
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
                name=doc.name,
                lastname=doc.lastname,
                email=doc.email,
                dni=doc.dni,
                speciality_id=doc.speciality_id,
                telephone=doc.telephone
            ))

        return ORJSONResponse(
            MedicalScheduleResponse(
                id=schedule.id,
                time_medic=schedule.time_medic,
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

@schedules.delete("/delete/{schedule_id}/", response_model=MedicalScheduleDelete)
async def delete_schedule(request: Request, session: SessionDep, schedule_id: str):
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
            ),
            status_code=status.HTTP_202_ACCEPTED
        )
    else:
        return ORJSONResponse({
            "error": f"Schedule {result.id} not found"
        }, status_code=status.HTTP_404_NOT_FOUND)

doctors = APIRouter(
    prefix="/doctors",
    tags=["doctors"],
    default_response_class=ORJSONResponse
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
                name=doc.name,
                lastname=doc.lastname,
                dni=doc.dni,
                telephone=doc.telephone,
                email=doc.email,
                speciality_id=doc.speciality_id
            ).model_dump()
        )

    return ORJSONResponse(doctors)

@doctors.post("/add/", response_model=DoctorResponse)
async def add_doctor(request: Request, doctor: DoctorCreate, session: SessionDep):
    try:
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
                name=new_doctor.name,
                lastname=new_doctor.lastname,
                dni=new_doctor.dni,
                telephone=new_doctor.telephone,
                email=new_doctor.email,
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

@doctors.get("/{doctor_id}/", response_model=DoctorResponse)
async def get_doctor_by_id(request: Request, dotor_id: str, session: SessionDep):
    statement = select(Doctors).where(Doctors.id == dotor_id)
    doc = session.execute(statement).scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Doctor {dotor_id} not found")

    return ORJSONResponse(
        DoctorResponse(
            id=doc.id,
            name=doc.name,
            lastname=doc.lastname,
            dni=doc.dni,
            telephone=doc.telephone,
            email=doc.email,
            speciality_id=doc.speciality_id
        )
    )

@doctors.delete("/delete/{doctor_id}/", response_model=DoctorDelete)
async def delete_doctor(request: Request, doctor_id: str, session: SessionDep):
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

@doctors.put("/update/{doctor_id}/", response_model=DoctorUpdate)
async def update_doctor(request: Request, doctor_id: str, session: SessionDep, doctor: DoctorUpdate):
    try:
        doc = session.excecute(
            select(Doctors)
                .where(Doctors.id == doctor_id)
        ).scalars().first()

        form_fields: List[str] = list(DoctorUpdate.__fields__.keys())


        for field in form_fields:
            if field is not None:
                setattr(doc, field, getattr(doctor, field))
            elif field == "password":
                doc.set_password(doctor.password)

        session.add(doc)
        session.commit()
        session.refresh(doc)

        return ORJSONResponse(
            DoctorUpdate(
                id=doc.id,
                name=doc.name,
                lastname=doc.lastname,
                dni=doc.dni,
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
                name=doc.name,
                lastname=doc.lastname,
                dni=doc.dni,
                telephone=doc.telephone,
                email=doc.email,
                speciality_id=doc.speciality_id
            )
        )
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=404, detail=f"Doctor {doc_id} not found")

locations = APIRouter(
    prefix="/locations",
    tags=["locations"],
)

@locations.get("/", response_model=List[LocationResponse])
async def get_locations(request: Request, session: SessionDep):
    statement = select(Locations)
    result = session.execute(statement).scalars().all()
    locations = []
    for location in result:
        statement = select(Departments).where(Departments.location_id == locations.id)
        result: List["Departments"] = session.execute(statement).scalars().all()
        departments = []
        for department in result:
            statement = select(Specialties).where(Specialties.department_id == department.id)
            result: List["Specialties"] = session.execute(statement).scalars().all()
            specialties = []
            for specialty in result:
                statement = select(Services).where(Services.specialty_id == specialty.id)
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
                statement = select(Doctors).where(Doctors.service_id == specialty.id)
                result: List["Doctors"] = session.execute(statement).scalars().all()
                doctors = []
                for doc in result:
                    doctors.append(
                        DoctorResponse(
                            id=doc.id,
                            name=doc.name,
                            lastname=doc.lastname,
                            dni=doc.dni,
                            telephone=doc.telephone,
                            email=doc.email,
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

services = APIRouter(
    prefix="/services",
    tags=["services"],
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

@services.delete("/delete/{service_id}/", response_model=ServiceResponse)
async def delete_service(request: Request, session: SessionDep, service_id :str):
    try:
        service = session.execute(select(Services).where(Services.id == services.id)).scalars().first()

        session.delete(service)
        session.commit()

        return ORJSONResponse({
            "service":ServiceResponse(
                id=service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                specialty_id=service.specialty_id
            ),
            "status":f"service {service.id} deleted"
        })
    except Exception as e:
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

specialities = APIRouter(
    prefix="/specialities",
    tags=["specialities"],
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
                    name=doc.name,
                    lastname=doc.lastname,
                    dni=doc.dni,
                    telephone=doc.telephone,
                    email=doc.email,
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

chat = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # user_id → WebSocket

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()  # Handshake HTTP→WS :contentReference[oaicite:4]{index=4}
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)  # envía JSON → cliente :contentReference[oaicite:5]{index=5}

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

    def is_connected(self, doc_id) -> bool:
        return doc_id in self.active_connections


manager = ConnectionManager()

@chat.post("/add")
async def create_chat(request: Request, session: SessionDep, doc: Doctors | User = Depends(auth), doc_2_id = Query(...)):

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
async def websocket_chat(websocket: WebSocket, session: SessionDep, chat_id, doc: Doctors | User = Depends(ws_auth)):
    try:
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
    dependencies=[
        Depends(auth)
    ]
)

router.include_router(schedules)
router.include_router(doctors)
router.include_router(locations)
router.include_router(services)
router.include_router(specialities)
router.include_router(chat)