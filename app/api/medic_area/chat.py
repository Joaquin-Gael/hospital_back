"""Chat and websocket routes for doctors."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket
from fastapi.responses import ORJSONResponse
from fastapi.websockets import WebSocketDisconnect
from sqlmodel import select

from app.db.main import SessionDep
from app.models import Chat, ChatMessages, Doctors, User
from app.schemas.medica_area import ChatResponse, DoctorResponse

from .common import auth, console, ws_auth


router = APIRouter(prefix="/chat", tags=["chat"])
ws_router = APIRouter(prefix="/ws")


class ConnectionManager:
    """Manage active websocket connections between doctors."""

    def __init__(self) -> None:
        self.active_connections: dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: UUID) -> None:
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: UUID) -> None:
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, message: dict) -> None:
        for websocket in self.active_connections.values():
            await websocket.send_json(message)

    def is_connected(self, doc_id: UUID) -> bool:
        return doc_id in self.active_connections


manager = ConnectionManager()


@router.get("/", response_model=List[ChatResponse])
async def get_chats(session: SessionDep):
    try:
        chats = session.exec(select(Chat)).all()

        chats_list: List[ChatResponse] = []
        for chat_i in chats:
            doctor_1 = session.exec(
                select(Doctors).where(Doctors.id == chat_i.doc_1_id)
            ).first()
            doctor_2 = session.exec(
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
                        speciality_id=doctor_1.speciality_id,
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
                        speciality_id=doctor_2.speciality_id,
                    ),
                ).model_dump()
            )

        return ORJSONResponse(chats_list)

    except Exception as exc:  # pragma: no cover - legacy behaviour
        console.print_exception(show_locals=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/add")
async def create_chat(
    request: Request, session: SessionDep, doc_2_id=Query(...), _=Depends(auth)
):
    if "doc" not in request.state.scopes:
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

    return ORJSONResponse({"message": f"Chat {new_chat.id} created"})


@ws_router.websocket("/chat/{chat_id}")
async def websocket_chat(
    websocket: WebSocket,
    session: SessionDep,
    chat_id,
    data: tuple = Depends(ws_auth),
):
    if data is None:
        raise WebSocketDisconnect()

    if "doc" not in data[1]:
        await websocket.close(1008, reason="Unauthorized")
        return

    doc: Doctors = data[0]

    try:
        if isinstance(doc, User):
            await websocket.close(1008, reason="You are not authorized")
            return

        chat_db = session.exec(select(Chat).where(Chat.id == chat_id)).first()

        if chat_db.doc_1_id != doc.id and chat_db.doc_2_id != doc.id:
            await websocket.close(1008, reason="doctor unauthorized")
            return
    except Exception:  # pragma: no cover - keep legacy logging
        console.print_exception(show_locals=True)
        await websocket.close(1008, reason="unknown error")
        return

    await manager.connect(doc.id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = data["content"]

            chat_db = session.exec(select(Chat).where(Chat.id == chat_id)).first()

            message = ChatMessages(
                sender_id=doc.id,
                chat_id=chat_id,
                content=content,
                chat=chat_db,
            )

            session.add(message)
            session.commit()
            session.refresh(message)

            if manager.is_connected(doc.id):
                await manager.send_personal_message(
                    {
                        "type": "message",
                        "message": {
                            "content": message.content,
                            "created_at": message.created_at.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        },
                    },
                    user_id=chat_db.doc_2_id,
                )
    except WebSocketDisconnect:
        pass


router.include_router(ws_router)

__all__ = ["router"]
