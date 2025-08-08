import os
from typing import List

from dotenv import load_dotenv

from pathlib import Path

from uuid import uuid4, UUID

from fastapi.templating import Jinja2Templates

from app.models import User

load_dotenv()

id_prefix: UUID = uuid4()

debug:bool = bool(int(os.getenv("DEBUG")))

templates_dir = Path(__file__).parent / "templates"

assets_dir = Path(__file__).parent / "assets"

media_dir = Path(__file__).parent / "media"

templates = Jinja2Templates(directory=templates_dir)

api_name = "Hospital API"
version = "0.2.7"

db_url = os.getenv("DB_URL")

cors_host = os.getenv("DOMINIO")

token_key = os.getenv("TOKEN_KEY")

google_client_secret = os.getenv("CLIENT_SECRET_GOOGLE")
google_client_id = os.getenv("CLIENT_ID_GOOGLE")
google_oauth_url = os.getenv("OAUTH_GOOGLE_URL")
google_oauth_token_url = os.getenv("OAUTH_GOOGLE_TOKEN_URL")
google_oauth_userinfo_url = os.getenv("OAUTH_GOOGLE_USERINFO_URL")

email_host = os.getenv("EMAIL_HOST")
email_port = int(os.getenv("EMAIL_PORT"))
email_use_tls = bool(int(os.getenv("EMAIL_USE_TLS")))
email_host_user = os.getenv("EMAIL_HOST_USER")
email_host_password = os.getenv("EMAIL_HOST_PASSWORD")

stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

admin_username = os.getenv("ADMIN_USERNAME")
admin_password = os.getenv("ADMIN_PASSWORD")
admin_email = os.getenv("ADMIN_EMAIL")


admin_user = User(
    name=admin_username,
    email=admin_email,
    password=admin_password,
    dni="00000000"
)
admin_user.set_password(
    admin_user.password
)
admin_user.make_superuser()

def parser_name(folders: List[str], name:str) -> str:
    return "/".join(folders) + f"/{name}.html"