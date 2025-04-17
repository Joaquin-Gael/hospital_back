from cryptography import fernet
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, VARCHAR

from datetime import datetime
from typing import Optional

from passlib.context import CryptContext

from uuid import UUID
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(SQLModel, table=True):
    id: Optional[str] = Field( # TODO: pasar a posgresql cambiar a UUID
        sa_column=Column(
            name="user_id",
            type_=String(36),
            primary_key=True,
            autoincrement="auto",
            unique=True,
        ),
        default_factory=lambda: str(uuid.uuid4()),
    )
    name: str = Field(
        sa_column=Column(
            name="username",
            type_=VARCHAR
        ),
        max_length=50
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
    
    def make_normaluser(self) -> bool:
        self.is_superuser = False
        self.is_admin = False
        return True

    def ban(self) -> bool:
        self.is_active = False
        return True

    def des_ban(self) -> bool:
        self.is_active = True
        return True