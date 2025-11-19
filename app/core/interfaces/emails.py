import smtplib
from email.message import EmailMessage

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.config import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    TEMPLATES,
    parser_name
)
from app.core.utils import BaseInterface


class MailSchema(BaseModel):
    to: EmailStr
    subject: str
    template_name: str
    context: dict
    
def send_email(to: str, subject: str, html_content: str, message: str):
    msg = EmailMessage()
    msg["From"] = EMAIL_HOST_USER
    msg["To"] = to
    msg["Subject"] = subject

    if message:
        msg.set_content("Tu cliente de correo no soporta HTML")
    else:
        msg.add_alternative(html_content, subtype="html")

    if EMAIL_USE_TLS:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)

    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    server.send_message(msg)
    server.quit()

class EmailService(BaseInterface):
    @staticmethod
    def _render_email(template_name: str, subject: str, context: dict) -> str:
        merged_context = {
            "request": {},
            "brand_name": "Hospital SDLG",
            "brand_tagline": "Cuidando tu salud con excelencia",
            "email_subject": subject,
            "action_summary": subject,
            **context,
        }

        return TEMPLATES.TemplateResponse(
            parser_name(folders=["emails"], name=rf"{template_name}"), merged_context
        ).body.decode("utf-8")

    @staticmethod
    def send_welcome_email(
        email: str,
        first_name: str,
        last_name: str,
        help_link: str | None = None,
        contact_number: str | None = None,
        contact_email: str | None = None,
        action_summary: str | None = None,
    ):
        subject = "Bienvenido a Hospital SDLG"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Bienvenido a Hospital SDLG",
        }
        html_content = EmailService._render_email("welcome_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_password_reset_email(
        email: str,
        reset_code: str,
        help_link: str | None = None,
        contact_number: str | None = None,
        contact_email: str | None = None,
        action_summary: str | None = None,
    ):
        subject = "Restablecimiento de contraseña"
        context = {
            "reset_code": reset_code,
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Restablecimiento de contraseña",
        }
        html_content = EmailService._render_email("password_reset_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_password_changed_notification_email(
        email: str,
        help_link: str,
        contact_number: str,
        contact_email: str,
        action_summary: str | None = None,
    ):
        subject = "Notificación de cambio de contraseña"
        context = {
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Cambio de contraseña",
        }
        html_content = EmailService._render_email("password_changed_notification_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_verification_email(
        email: str,
        verification_code: str,
        help_link: str | None = None,
        contact_number: str | None = None,
        contact_email: str | None = None,
        action_summary: str | None = None,
    ):
        subject = "Verificación de correo electrónico"
        context = {
            "verification_code": verification_code,
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Verificación de correo electrónico",
        }
        html_content = EmailService._render_email("verification_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_update_data_notification_email(email, first_name: str, last_name: str, data_to_update: dict):
        subject = "Actualización de datos"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "data_to_update": data_to_update, # Nombre de el campo y el porque
            "action_summary": "Actualización de información",
        }
        html_content = EmailService._render_email("update_data_notification_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_google_account_linked_password(
        email: str,
        first_name: str,
        last_name: str,
        raw_password: str,
        help_link: str | None = None,
        contact_number: str | None = None,
        contact_email: str | None = None,
        action_summary: str | None = None,
    ):
        subject = "Cuenta de Google vinculada"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "provisional_password": raw_password,
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Cuenta de Google vinculada",
        }
        html_content = EmailService._render_email("google_account_linked_email", subject, context)

        send_email(email, subject, html_content, None)

    @staticmethod
    def send_warning_google_account(
        email: str,
        first_name: str,
        last_name: str,
        created: datetime,
        to_delete: datetime,
        help_link: str | None = None,
        contact_number: str | None = None,
        contact_email: str | None = None,
        action_summary: str | None = None,
    ):
        days = to_delete - created

        subject = "Cuenta de Google vinculada"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "days": days,
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email,
            "action_summary": action_summary or "Advertencia de cuenta",
        }
        html_content = EmailService._render_email("warning_google_account_email", subject, context)

        send_email(email, subject, html_content, None)
