import random

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_user, logout_user

from src.auth import bp
from src.extensions import bcrypt, db
from src.models import User
from src.services.mailer import send_verification_code


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Todos los campos son obligatorios", "danger")
        else:
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                flash("Logueado correctamente", "success")
                return redirect(url_for("main.root"))
            flash("Contraseña o email incorrecto", "warning")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada", "success")
    return redirect(url_for("main.root"))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        nombre = request.form.get("name", "").strip()
        apellido = request.form.get("surname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or not password or not confirm:
            flash("Todos los campos son obligatorios", "danger")
        elif User.query.filter_by(email=email).first():
            flash("El usuario ya existe", "warning")
        elif password != confirm:
            flash("Las contraseñas deben coincidir", "warning")
        else:
            code = f"{random.randint(100000, 999999)}"
            session["pending_signup"] = {
                "name": f"{nombre} {apellido}".strip(),
                "email": email,
                "password": bcrypt.generate_password_hash(password).decode("utf-8"),
                "code": code,
            }
            send_verification_code(email, code)
            return render_template("email_verification.html")

    return render_template("auth/signup.html")


@bp.route("/mail/verification", methods=["POST"])
def email_verification():
    pending = session.get("pending_signup")
    if not pending:
        flash("La sesión expiró, vuelve a registrarte", "warning")
        return redirect(url_for("auth.signup"))

    if request.form.get("code_form") != pending["code"]:
        flash("El código no es correcto", "warning")
        return render_template("email_verification.html")

    user = User(
        name=pending["name"],
        email=pending["email"],
        password=pending["password"],
        role_id=1,
    )
    db.session.add(user)
    db.session.commit()
    session.pop("pending_signup", None)

    flash("Cliente creado exitosamente", "success")
    return redirect(url_for("auth.login"))


@bp.route("/login/google")
def login_google():
    return render_template("auth/signup.html")


@bp.route("/signup/google")
def signup_google():
    return render_template("auth/signup.html")
