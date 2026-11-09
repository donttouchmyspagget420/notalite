import random

from flask import flash, redirect, render_template, request, session, url_for
from flask_bcrypt import check_password_hash
from flask_login import login_user, logout_user

from src.auth import bp
from src.extensions import bcrypt, db
from src.models import User,Pending
from src.services.forms import LoginForm, SignupForm, VerificationForm, form_error
from src.services.mailer import send_verification_code
from src.services.google import getUserInfo,googleUri


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.password and bcrypt.check_password_hash(
            user.password, form.password.data
        ):
            login_user(user)
            flash("Logueado correctamente", "success")
            return redirect(url_for("notes.list_notes"))

        flash("Contraseña o email incorrecto", "warning")
    elif request.method == "POST":
        flash(form_error(form), "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada", "success")
    return redirect(url_for("main.root"))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        email = form.email.data

        if User.query.filter_by(email=email).first():
            flash("El usuario ya existe", "warning")
        else:
            code = f"{random.randint(100000, 999999)}"
            password_hash = bcrypt.generate_password_hash(
                form.password.data
            ).decode("utf-8")

            pending = Pending.query.filter_by(email=email).first()

            if pending:
                pending.name = f"{form.name.data} {form.surname.data}"
                pending.password = password_hash
                pending.code = code
                pending.role_id = 1
            else:
                pending = Pending(
                    name=f"{form.name.data} {form.surname.data}",
                    email=email,
                    password=password_hash,
                    role_id=1,
                    code=code,
                )
                db.session.add(pending)

            db.session.commit()

            session["pending_signup_email"] = pending.email
            send_verification_code(email, code)

            return render_template("email_verification.html")
    elif request.method == "POST":
        flash(form_error(form), "danger")

    return render_template("auth/signup.html", form=form)


@bp.route("/mail/verification", methods=["POST"])
def email_verification():
    email = session.get("pending_signup_email")
    pending = Pending.query.filter_by(email=email).first() if email else None

    if not pending:
        flash("La sesión expiró, vuelve a registrarte", "warning")
        return redirect(url_for("auth.signup"))

    form = VerificationForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return render_template("email_verification.html", form=form)

    if form.code_form.data != pending.code:
        flash("El código no es correcto", "warning")
        return render_template("email_verification.html", form=form)

    user = User(
        name=pending.name,
        email=pending.email,
        password=pending.password,
        role_id=pending.role_id,
    )

    db.session.add(user)
    db.session.delete(pending)
    db.session.commit()
    session.pop("pending_signup_email", None)

    login_user(user)

    flash("Cliente creado exitosamente", "success")
    return  redirect(url_for("notes.list_notes")) 

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
    return  redirect(url_for("notes.list_notes")) 
    

