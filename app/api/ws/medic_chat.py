from starlette.requests import Request

from fastapi import APIRouter

from sqlmodel import select

import socketio # TODO: ca,biarlo lo mas antes posible

from app.core.auth import decode_token
from app.models.users import User
from app.db.main import Session, engine

router = APIRouter(
    prefix="/medic_chat",
)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=["*"],
    cors_allowed_methods=["*"],
    cors_allow_headers=["*"],
    cors_credentials=True,
)

sio_app = socketio.ASGIApp(sio, other_asgi_app=router)
router.mount("/ws", sio_app, name="websocket")

@sio.event
async def connect(sid, environ):
    request = Request(environ)
    token = request.headers.get("authorization")
    if not token or not token.startswith("Bearer"):
        return False

    token = token.split(" ")[1]
    payload: dict = decode_token(token)

    with Session(engine) as session:
        statement = select(User).where(User.id == payload["sub"])
        user: User | None = session.execute(statement).scalars().first()

    if user is None:
        return False

    await sio.save_session(sid, {"user": user})

    return True


PRIVATE_NS = "/private"

@sio.on("join", namespace=PRIVATE_NS)
async def join_chat(sid, data):
    room = f"pv_{min(sid,data['with_id'])}_{max(sid,data['with_id'])}"
    await sio.enter_room(sid, room, namespace=PRIVATE_NS)
    await sio.emit("info", {"msg": f"Has entrado al privado {room}"}, room=sid, namespace=PRIVATE_NS)

@sio.on("message", namespace=PRIVATE_NS)
async def private_message(sid, data):
    """
    data: {
      "to_id": "<otro_sid_o_user_id>",
      "msg": "hola"
    }
    """
    # Calculamos la misma room para ambos usuarios
    room = f"pv_{min(sid,data['to_id'])}_{max(sid,data['to_id'])}"
    session = await sio.get_session(sid)
    user: User = session.get("user",None)
    await sio.emit("message", {"from": user.name, "msg": data["msg"]}, room=room, namespace=PRIVATE_NS)


# TODO: pasar a ws nativos de fastapi