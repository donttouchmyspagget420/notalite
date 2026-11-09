"""WTForms definitions shared by the application blueprints."""

import os

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    PasswordField,
    SelectField,
    StringField,
)
from wtforms.validators import (
    AnyOf,
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    Regexp,
    ValidationError,
)

from src.enums import NoteLength, UploadLimit
from src.services.storage import IMAGE_EXTENSIONS


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def _first_error(form):
    """Return the first validation error message for flashing."""
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Revisá los datos del formulario."


class MaxFileSize:
    """Validate the real size of an uploaded file."""

    def __init__(self, max_bytes, message=None):
        self.max_bytes = max_bytes
        self.message = message

    def __call__(self, form, field):
        upload = field.data
        if not upload:
            return

        stream = upload.stream
        position = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(position)

        if size > self.max_bytes:
            limit_mb = self.max_bytes // (1024 * 1024)
            raise ValidationError(
                self.message or f"La imagen supera el máximo de {limit_mb} MB."
            )


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[_strip],
        validators=[DataRequired("El email es obligatorio."), Email("Ingresá un email válido.")],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired("La contraseña es obligatoria.")],
    )


class SignupForm(FlaskForm):
    name = StringField(
        "Nombre",
        filters=[_strip],
        validators=[
            DataRequired("El nombre es obligatorio."),
            Length(max=NoteLength.NAME, message="El nombre es demasiado largo."),
        ],
    )
    surname = StringField(
        "Apellido",
        filters=[_strip],
        validators=[
            DataRequired("El apellido es obligatorio."),
            Length(max=NoteLength.NAME, message="El apellido es demasiado largo."),
        ],
    )
    email = StringField(
        "Email",
        filters=[_strip],
        validators=[
            DataRequired("El email es obligatorio."),
            Email("Ingresá un email válido."),
            Length(max=NoteLength.TITLE, message="El email es demasiado largo."),
        ],
    )
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired("La contraseña es obligatoria."),
            Length(min=8, max=255, message="La contraseña debe tener al menos 8 caracteres."),
        ],
    )
    confirm_password = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired("Confirmá la contraseña."),
            EqualTo("password", message="Las contraseñas deben coincidir."),
        ],
    )


class VerificationForm(FlaskForm):
    code_form = StringField(
        "Código",
        filters=[_strip],
        validators=[
            DataRequired("El código es obligatorio."),
            Regexp(r"^\d{6}$", message="El código debe tener 6 dígitos."),
        ],
    )


class ProfileForm(FlaskForm):
    name = StringField(
        "Nombre",
        filters=[_strip],
        validators=[
            DataRequired("El nombre es obligatorio."),
            Length(max=NoteLength.NAME, message="El nombre es demasiado largo."),
        ],
    )
    email = StringField(
        "Email",
        filters=[_strip],
        validators=[
            DataRequired("El email es obligatorio."),
            Email("Ingresá un email válido."),
            Length(max=NoteLength.TITLE, message="El email es demasiado largo."),
        ],
    )
    avatar = StringField(
        "URL del avatar",
        filters=[_strip],
        validators=[Optional(), Length(max=NoteLength.TITLE)],
    )


class PasswordForm(FlaskForm):
    current_password = PasswordField("Contraseña actual", validators=[Optional()])
    new_password = PasswordField(
        "Nueva contraseña",
        validators=[
            DataRequired("La contraseña nueva es obligatoria."),
            Length(min=8, max=255, message="La contraseña debe tener al menos 8 caracteres."),
        ],
    )
    confirm_password = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired("Confirmá la contraseña nueva."),
            EqualTo("new_password", message="Las contraseñas nuevas deben coincidir."),
        ],
    )


class ThemeForm(FlaskForm):
    theme = StringField(
        "Tema",
        validators=[AnyOf(["dark", "light"], message="El tema elegido no es válido.")],
    )


class FolderForm(FlaskForm):
    name = StringField(
        "Nombre",
        filters=[_strip],
        validators=[
            DataRequired("El nombre de la carpeta es obligatorio."),
            Length(max=NoteLength.NAME, message="El nombre es demasiado largo."),
        ],
    )
    parent_id = StringField("Carpeta padre", validators=[Optional()])


class TagForm(FlaskForm):
    name = StringField(
        "Nombre",
        filters=[_strip],
        validators=[
            DataRequired("El nombre de la etiqueta es obligatorio."),
            Length(max=NoteLength.NAME, message="El nombre es demasiado largo."),
        ],
    )


class MoveNoteForm(FlaskForm):
    directory_id = StringField("Carpeta", validators=[Optional()])


class ShareNoteForm(FlaskForm):
    user_id = StringField(
        "Usuario",
        filters=[_strip],
        validators=[DataRequired("Elegí una cuenta para compartir.")],
    )
    permission = SelectField(
        "Permiso",
        choices=[("view", "Solo lectura"), ("edit", "Puede editar")],
        default="view",
        validators=[AnyOf(["view", "edit"], message="El permiso no es válido.")],
    )


class ImageUploadForm(FlaskForm):
    image = FileField(
        "Imagen",
        validators=[
            FileRequired("Elegí una imagen para subir."),
            FileAllowed(
                IMAGE_EXTENSIONS,
                message="Formato no permitido. Usá PNG, JPG, GIF o WebP.",
            ),
            MaxFileSize(UploadLimit.IMAGE_BYTES),
        ],
    )
    alt = StringField(
        "Descripción",
        filters=[_strip],
        validators=[Optional(), Length(max=255)],
    )


def form_error(form):
    """Public helper used by routes to flash a single readable error."""
    return _first_error(form)
