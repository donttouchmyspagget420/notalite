import random

from flask import flash, redirect, render_template, request, session, url_for
from flask_bcrypt import check_password_hash
from flask_login import login_user, logout_user

from src.auth import bp
from src.extensions import bcrypt, db
from src.models import User,Pending
from src.services.mailer import send_verification_code
from src.services.google import getUserInfo,googleUri


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

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
        name = request.form.get("name")
        surname = request.form.get("surname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if not email or not password or not confirm:
            flash("Todos los campos son obligatorios", "danger")
        elif User.query.filter_by(email=email).first():
            flash("El usuario ya existe", "warning")
        elif password != confirm:
            flash("Las contraseñas deben coincidir", "warning")
        else:
            code = f"{random.randint(100000, 999999)}"

            pending = Pending(
                name=name + " " + surname,
                email=email,
                password=bcrypt.generate_password_hash(password),
                role_id=1,
                code=code
            )

            db.session.add(pending)
            db.session.commit()

            session["pending_signup_email"] = pending.email; 
            send_verification_code(email, code)

            return render_template("email_verification.html")

    return render_template("auth/signup.html")


@bp.route("/mail/verification", methods=["POST"])
def email_verification():
    pending = Pending.query.filter_by(email=session["pending_signup_email"]).first()
    if not pending:
        flash("La sesión expiró, vuelve a registrarte", "warning")
        return redirect(url_for("auth.signup"))

    code_form = request.form.get("code_form")

    if code_form != pending.code:
        flash("El código no es correcto", "warning")
        return render_template("email_verification.html")

    user = User(
        name=pending.name,
        email=pending.email,
        password=pending.password,
        role_id=pending.role_id,
    )

    db.session.add(user)
    db.session.commit()
    session.pop("pending_signup_email", None)

    login_user(user)

    flash("Cliente creado exitosamente", "success")
    return redirect(url_for("main.root"))

@bp.route("/login/google")
def login_google():
    return googleUri()

@bp.route("/google/callback")
def callback_google():
    userinfo = getUserInfo()
    if not userinfo:
        flash("no puede obtener la informacion de usuario","danger")
        return redirect(url_for('auth.signup'))
    
    user = User.query.filter_by(g_id = userinfo["sub"]).first()
    if not user:
        user = User(
            g_id = userinfo["sub"],
            email = userinfo["email"],
            name = userinfo["name"],
            avatar = userinfo["picture"],
            role_id = 1
        )

        db.session.add(user)
        db.session.commit()

    login_user(user)

    flash("Logueado exitosamente", "success")
    return redirect(url_for('main.root'))
    
