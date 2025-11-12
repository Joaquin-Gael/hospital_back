from types import SimpleNamespace

import orjson
import pytest

from fastapi import HTTPException, Request, status

from app.api.users import update_user_password
from app.core.interfaces.emails import EmailService
from app.models import User
from app.schemas.users import UserPasswordUpdate


async def _empty_receive() -> dict:
    return {"type": "http.request", "body": b"", "more_body": False}


def _build_request(user_id, is_superuser: bool = False) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "PATCH",
        "scheme": "http",
        "path": f"/users/{user_id}/password",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"user-agent", b"pytest"), (b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "app": None,
    }
    request = Request(scope, _empty_receive)
    request.state.user = SimpleNamespace(id=user_id, is_superuser=is_superuser)
    return request


class DummySession:
    def __init__(self, user: User):
        self._user = user
        self.added = []
        self.committed = False
        self.refreshed = []

    def get(self, model, user_id):
        if model is User and user_id == self._user.id:
            return self._user
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


class DummyEmitter:
    def __init__(self):
        self.events = []

    async def emit_event(self, event):
        self.events.append(event)


def _make_user() -> User:
    user = User(
        name="TestUser",
        email="user@example.com",
        password="TempPass1!",
        dni="12345678",
    )
    user.set_password("OldPass1!")
    return user


@pytest.mark.asyncio
async def test_update_user_password_accepts_two_fields(monkeypatch):
    user = _make_user()
    session = DummySession(user)
    emitter = DummyEmitter()
    request = _build_request(user.id)

    notifications = []

    def fake_notification(email: str, help_link: str, contact_number: str, contact_email: str):
        notifications.append((email, help_link, contact_number, contact_email))

    monkeypatch.setattr(
        EmailService,
        "send_password_changed_notification_email",
        staticmethod(fake_notification),
    )

    payload = UserPasswordUpdate(old_password="OldPass1!", new_password="NewPass2!")
    response = await update_user_password(request, user.id, session, payload, emitter)

    assert response.status_code == status.HTTP_200_OK
    assert session.committed is True
    assert user.check_password("NewPass2!") is True
    assert len(emitter.events) == 1
    assert notifications

    body = orjson.loads(response.body)
    assert body["id"] == str(user.id)


@pytest.mark.asyncio
async def test_update_user_password_invalid_current_password(monkeypatch):
    user = _make_user()
    session = DummySession(user)
    emitter = DummyEmitter()
    request = _build_request(user.id)

    monkeypatch.setattr(
        EmailService,
        "send_password_changed_notification_email",
        staticmethod(lambda *args, **kwargs: None),
    )

    payload = UserPasswordUpdate(old_password="WrongPass1!", new_password="NewPass2!")

    with pytest.raises(HTTPException) as exc:
        await update_user_password(request, user.id, session, payload, emitter)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert not session.committed


@pytest.mark.asyncio
async def test_update_user_password_mismatched_confirmation(monkeypatch):
    user = _make_user()
    session = DummySession(user)
    emitter = DummyEmitter()
    request = _build_request(user.id)

    monkeypatch.setattr(
        EmailService,
        "send_password_changed_notification_email",
        staticmethod(lambda *args, **kwargs: None),
    )

    payload = UserPasswordUpdate(
        old_password="OldPass1!",
        new_password="NewPass2!",
        new_password_confirm="Different3#",
    )

    with pytest.raises(HTTPException) as exc:
        await update_user_password(request, user.id, session, payload, emitter)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert not session.committed
