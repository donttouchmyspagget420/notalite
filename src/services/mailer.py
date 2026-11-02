import smtplib

from flask import current_app, flash
from flask_mailman import BadHeaderError, EmailMessage


def send_verification_code(email, code):
    msg = EmailMessage(
        subject="NotaLite - verificar el mail",
        body=f"Verifica tu email ingresando el código: {code} para registrarte",
        to=[email],
        from_email=current_app.config["MAIL_DEFAULT_SENDER"],
    )
    try:
        msg.send()
        flash("Correo electrónico enviado con éxito.", "success")
    except BadHeaderError:
        flash("Encabezado no válido detectado.", "danger")
    except (ConnectionRefusedError, smtplib.SMTPException):
        flash("No se pudo conectar con el servidor de correo.", "danger")
    except Exception:
        current_app.logger.exception("Fallo al enviar correo de verificación")
        flash("Ocurrió un error al enviar el correo.", "danger")
