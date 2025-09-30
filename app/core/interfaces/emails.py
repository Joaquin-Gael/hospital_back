import smtplib
from email.message import EmailMessage

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.config import (
    email_host,
    email_port,
    email_use_tls,
    email_host_user,
    email_host_password,
    templates,
    parser_name
)


class MailSchema(BaseModel):
    to: EmailStr
    subject: str
    template_name: str
    context: dict
    
def send_email(to: str, subject: str, html_content: str, message: str):
    msg = EmailMessage()
    msg["From"] = email_host_user
    msg["To"] = to
    msg["Subject"] = subject

    if message:
        msg.set_content("Tu cliente de correo no soporta HTML")
    else:
        msg.add_alternative(html_content, subtype="html")

    if email_use_tls:
        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(email_host, email_port)

    server.login(email_host_user, email_host_password)
    server.send_message(msg)
    server.quit()
    
class EmailService:
    @staticmethod
    def send_welcome_email(email: str, first_name: str, last_name: str):
        subject = "Bienvenido a Hospital SDLG"
        context = {
            "first_name": first_name,
            "last_name": last_name
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"welcome_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)
    
    @staticmethod
    def send_password_reset_email(email: str, reset_code: str):
        subject = "Restablecimiento de contraseña"
        context = {
            "reset_code": reset_code
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"password_reset_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)
        
    @staticmethod
    def send_password_changed_notification_email(email: str, help_link: str, contact_number: str, contact_email: str):
        subject = "Notificación de cambio de contraseña"
        context = {
            "help_link": help_link,
            "contact_number": contact_number,
            "contact_email": contact_email
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"password_changed_notification_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)
        
    @staticmethod
    def send_verification_email(email: str, verification_code: str):
        subject = "Verificación de correo electrónico"
        context = {
            "verification_code": verification_code
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"verification_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)
        
    @staticmethod
    def send_update_data_notification_email(email, first_name: str, last_name: str, data_to_update: dict):
        subject = "Actualización de datos"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "data_to_update": data_to_update # Nombre de el campo y el porque
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"update_data_notification_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)
        
    @staticmethod
    def send_google_account_linked_password(email: str, first_name: str, last_name: str, raw_password: str):
        subject = "Cuenta de Google vinculada"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "provisional_password": raw_password
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"google_account_linked_email"), {"request": {}, **context}
        ).body.decode("utf-8")
        
        send_email(email, subject, html_content, None)

    @staticmethod
    def send_warning_google_account(email: str, first_name: str, last_name: str, created: datetime, to_delete: datetime):
        days = to_delete - created

        subject = "Cuenta de Google vinculada"
        context = {
            "first_name": first_name,
            "last_name": last_name,
            "days": days
        }
        html_content = templates.TemplateResponse(
            parser_name(folders=["emails"], name=r"warning_google_account_email"), {"request": {}, **context}
        ).body.decode("utf-8")

        send_email(email, subject, html_content, None)