import os
from typing import List

from dotenv import load_dotenv

from pathlib import Path

from uuid import uuid4, UUID

from fastapi.templating import Jinja2Templates

from app.models import User

load_dotenv()

id_prefix: UUID = uuid4()

def _get_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


debug: bool = _get_env_bool("DEBUG", False)

templates_dir = Path(__file__).parent / "templates"

assets_dir = Path(__file__).parent / "assets"

media_dir = Path(__file__).parent / "media"

templates = Jinja2Templates(directory=templates_dir)

binaries_dir = Path(__file__).parent / "core" / "binaries"

api_name = "Hospital API"
version = "0.10.7"

db_url = os.getenv("DB_URL")

cors_host = os.getenv("DOMINIO")

token_key = os.getenv("TOKEN_KEY")

google_client_secret = os.getenv("CLIENT_SECRET_GOOGLE")
google_client_id = os.getenv("CLIENT_ID_GOOGLE")
google_oauth_url = os.getenv("OAUTH_GOOGLE_URL")
google_oauth_token_url = os.getenv("OAUTH_GOOGLE_TOKEN_URL")
google_oauth_userinfo_url = os.getenv("OAUTH_GOOGLE_USERINFO_URL")

email_host = os.getenv("EMAIL_HOST")
email_port = _get_env_int("EMAIL_PORT", 587)
email_use_tls = _get_env_bool("EMAIL_USE_TLS", False)
email_host_user = os.getenv("EMAIL_HOST_USER")
email_host_password = os.getenv("EMAIL_HOST_PASSWORD")

stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

admin_username = os.getenv("ADMIN_USERNAME", "admin")
admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

llm_model_name = os.getenv("LLM_MODEL_NAME", "gpt2")


audit_enabled = _get_env_bool("AUDIT_ENABLED", True)

audit_minimum_severity = os.getenv("AUDIT_MINIMUM_SEVERITY", "info").lower()

audit_retention_days_raw = _get_env_int("AUDIT_RETENTION_DAYS", 180)
audit_retention_days = audit_retention_days_raw if audit_retention_days_raw > 0 else 0

audit_queue_size = _get_env_int("AUDIT_QUEUE_SIZE", 512)
audit_batch_size = _get_env_int("AUDIT_BATCH_SIZE", 50)
audit_linger_seconds = _get_env_float("AUDIT_LINGER_SECONDS", 0.5)
audit_retry_delay = _get_env_float("AUDIT_RETRY_DELAY", 1.0)

audit_list_default_limit = _get_env_int("AUDIT_LIST_DEFAULT_LIMIT", 100)
audit_list_max_limit = _get_env_int("AUDIT_LIST_MAX_LIMIT", 500)
audit_export_default_limit = _get_env_int("AUDIT_EXPORT_DEFAULT_LIMIT", 1000)
audit_export_max_limit = _get_env_int("AUDIT_EXPORT_MAX_LIMIT", 2000)

audit_redact_fields = {
    value.strip().lower()
    for value in os.getenv("AUDIT_REDACT_FIELDS", "password,token,secret").split(",")
    if value.strip()
}


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