import os
from dotenv import load_dotenv

from app.models import User, PasswordError

load_dotenv()

debug:bool = bool(int(os.getenv("DEBUG")))

api_name = "Hospital API"
version = "0.2.7"

cors_host = os.getenv("DOMINIO")

token_key = os.getenv("TOKEN_KEY")

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