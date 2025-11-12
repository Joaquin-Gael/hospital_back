import os
from typing import List

from dotenv import load_dotenv

from pathlib import Path

from uuid import uuid4, UUID

from datetime import datetime

from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates

from app.models import User

load_dotenv()

TIME_ZONE = ZoneInfo(os.getenv("TIME_ZONE", "America/Argentina/Buenos_Aires"))


def GET_CURRENT_TIME() -> datetime:
    return datetime.now(TIME_ZONE)

ID_PREFIX: UUID = uuid4()

DEBUG: bool = bool(int(os.getenv("DEBUG")))

TEMPLATES_DIR = Path(__file__).parent / "templates"

ASSETS_DIR = Path(__file__).parent / "assets"

MEDIA_DIR = Path(__file__).parent / "media"

TEMPLATES = Jinja2Templates(directory=TEMPLATES_DIR)

BINARIES_DIR = Path(__file__).parent / "core" / "binaries"

API_NAME = "Hospital API"
VERSION = "0.10.7"

DB_URL = os.getenv("DB_URL")

REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_DB = int(os.getenv("REDIS_DB"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_SSL = os.getenv("REDIS_SSL") == "True"

STORAGE_DIR_NAME = os.getenv("STORAGE_DIR_NAME", "sets")

CORS_HOST = os.getenv("DOMINIO")

TOKEN_KEY = os.getenv("TOKEN_KEY")

GOOGLE_CLIENT_SECRET = os.getenv("CLIENT_SECRET_GOOGLE")
GOOGLE_CLIENT_ID = os.getenv("CLIENT_ID_GOOGLE")
GOOGLE_OAUTH_URL = os.getenv("OAUTH_GOOGLE_URL")
GOOGLE_OAUTH_TOKEN_URL = os.getenv("OAUTH_GOOGLE_TOKEN_URL")
GOOGLE_OAUTH_USERINFO_URL = os.getenv("OAUTH_GOOGLE_USERINFO_URL")

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USE_TLS = bool(int(os.getenv("EMAIL_USE_TLS")))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt2")


ADMIN_USER = User(
    name=ADMIN_USERNAME,
    email=ADMIN_EMAIL,
    password=ADMIN_PASSWORD,
    dni="00000000"
)
ADMIN_USER.set_password(
    ADMIN_USER.password
)
ADMIN_USER.make_superuser()

def parser_name(folders: List[str], name: str) -> str:
    return "/".join(folders) + f"/{name}.html"
