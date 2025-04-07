import os
from dotenv import load_dotenv

from app.models.users import User

load_dotenv()

admin_username = os.getenv("ADMIN_USERNAME")
admin_password = os.getenv("ADMIN_PASSWORD")
admin_email = os.getenv("ADMIN_EMAIL")

admin_user = User(
    name=admin_username,
    email=admin_email,
    password=admin_password
)
admin_user.set_password(
    admin_user.password
)
admin_user.make_superuser()