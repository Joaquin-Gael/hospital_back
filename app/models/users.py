from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, VARCHAR, UUID as SQLUUID

from datetime import datetime
from typing import Optional

from passlib.context import CryptContext

from uuid import UUID
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class BaseUser(SQLModel, table=False):
    name: str = Field(
        sa_type=VARCHAR(length=32),
        max_length=50,
        sa_column_kwargs={"name":"username"}
    )
    email: str = Field(unique=True, index=True)
    first_name: Optional[str] = Field(nullable=True)
    last_name: Optional[str] = Field(nullable=True)
    password: str = Field()
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    last_login: Optional[datetime] = Field(nullable=True)
    date_joined: datetime = Field(default_factory=datetime.now)
    dni: str = Field(max_length=8)
    telephone: Optional[str] = Field(max_length=50)
    address: Optional[str] = Field(nullable=True)


    def set_password(self, raw_password: str):
        """Genera y almacena el hash de la contraseña."""
        self.password = pwd_context.hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verifica la contraseña en texto plano contra el hash almacenado."""
        return pwd_context.verify(raw_password, self.password)

    def get_full_name(self) -> str:
        """Devuelve el nombre completo del usuario."""
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name if full_name else self.username

    def get_short_name(self) -> str:
        """Devuelve el nombre corto del usuario."""
        return self.first_name if self.first_name else self.username

    def make_superuser(self) -> bool:
        self.is_superuser = True
        self.is_admin = True
        return True
    
    def make_normal_user(self) -> bool:
        self.is_superuser = False
        self.is_admin = False
        return True

    def ban(self) -> bool:
        self.is_active = False
        return True

    def des_ban(self) -> bool:
        self.is_active = True
        return True

class User(BaseUser, table=True):
    __tablename__ = "users"
    id: Optional[UUID] = Field( # TODO: pasar a postgres cambiar a UUID
        sa_column=Column(
            name="user_id",
            type_=SQLUUID,
            primary_key=True,
            unique=True,
        ),
        default_factory=uuid.uuid4,
    )