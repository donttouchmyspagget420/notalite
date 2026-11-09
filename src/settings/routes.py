from flask import flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required

from src.extensions import bcrypt, db
from src.models import User
from src.services.forms import (
    PasswordForm,
    ProfileForm,
    ThemeForm,
    form_error,
)
from src.settings import bp


@bp.route("/")
@login_required
def profile():
    return render_template("settings/profile.html")


@bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    form = ProfileForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return redirect(url_for("settings.profile"))

    email = form.email.data
    existing = User.query.filter(
        User.email == email, User.id != current_user.id
    ).first()

    if existing:
        flash("Ese email ya está en uso.", "warning")
        return redirect(url_for("settings.profile"))

    current_user.name = form.name.data
    current_user.email = email
    current_user.avatar = form.avatar.data or None
    db.session.commit()

    flash("Perfil actualizado.", "success")
    return redirect(url_for("settings.profile"))


@bp.route("/password", methods=["POST"])
@login_required
def update_password():
    form = PasswordForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return redirect(url_for("settings.profile"))

    if current_user.password and not bcrypt.check_password_hash(
        current_user.password, form.current_password.data or ""
    ):
        flash("La contraseña actual no es correcta.", "danger")
        return redirect(url_for("settings.profile"))

    current_user.password = bcrypt.generate_password_hash(
        form.new_password.data
    ).decode("utf-8")
    db.session.commit()

    flash("Contraseña actualizada.", "success")
    return redirect(url_for("settings.profile"))


@bp.route("/theme", methods=["POST"])
@login_required
def update_theme():
    form = ThemeForm()

    if form.validate_on_submit():
        session["theme"] = form.theme.data
    else:
        flash(form_error(form), "warning")

    return redirect(url_for("settings.profile"))
