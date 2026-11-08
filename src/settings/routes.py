from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from src.enums import NoteLength
from src.extensions import bcrypt, db
from src.models import User
from src.settings import bp


@bp.route("/")
@login_required
def profile():
    return render_template("settings/profile.html")


@bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name")
    email = request.form.get("email")
    avatar = request.files["avatar"]

    if not name or not email:
        flash("El nombre y el email son obligatorios.", "warning")
        return redirect(url_for("settings.profile"))

    existing = User.query.filter(
        User.email == email, User.id != current_user.id
    ).first()

    if existing:
        flash("Ese email ya está en uso.", "warning")
        return redirect(url_for("settings.profile"))

    current_user.name = name[:NoteLength.NAME]
    current_user.email = email[:NoteLength.TITLE]
    current_user.avatar = avatar[:NoteLength.TITLE] or None
    db.session.commit()

    flash("Perfil actualizado.", "success")
    return redirect(url_for("settings.profile"))


@bp.route("/password", methods=["POST"])
@login_required
def update_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not new_password or new_password != confirm_password:
        flash("Las contraseñas nuevas deben coincidir.", "warning")
        return redirect(url_for("settings.profile"))

    if len(new_password) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "warning")
        return redirect(url_for("settings.profile"))

    if current_user.password and not bcrypt.check_password_hash(
        current_user.password, current_password
    ):
        flash("La contraseña actual no es correcta.", "danger")
        return redirect(url_for("settings.profile"))

    current_user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()

    flash("Contraseña actualizada.", "success")
    return redirect(url_for("settings.profile"))


@bp.route("/theme", methods=["POST"])
@login_required
def update_theme():
    theme = request.form.get("theme", "dark")
    session["theme"] = theme if theme in {"dark", "light"} else "dark"
    return redirect(url_for("settings.profile"))
