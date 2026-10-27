from flask import Flask, render_template, request, session, flash
from flask_bcrypt import Bcrypt, check_password_hash
from flask_login import LoginManager, login_user
from flask_wtf import CSRFProtect
from models import db,User
from dotenv import load_dotenv
from flask_mailman import Mail,EmailMessage,BadHeaderError
import os
import smtplib
import random

load_dotenv()

app = Flask(__name__)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] =os.getenv('MAIL_PORT') 
app.config['MAIL_USE_TLS'] =os.getenv('MAIL_USE_TLS') 
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] =os.getenv('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] =os.getenv('MAIL_DEFAULT_SENDER') 

app.secret_key = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")

db.init_app(app)

bcrypt = Bcrypt(app)
csrf = CSRFProtect(app);
login_manager = LoginManager(app)
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def root():
    return render_template('index.html')

@app.route('/auth/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]
        if not email and not password:
            flash("Todos los campos son obligatorios","danger")
        else:
            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                session["email"] = email
                flash("logueado correctamente","success")
                return render_template("index.html")

            flash("wrong password or login","warning")
        
    return render_template('auth/login.html')

@app.route('/auth/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        nombre = request.form["name"]
        apellido = request.form["surname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not email or not password or not confirm_password:
            flash("Todos los campos son obligatorios","danger")
        elif User.query.filter_by(email=email).first():
            flash("usuario ya existe","warning")
        elif password != confirm_password:
            flash("las contraseñas deben coincidir","warning")
        else:
            hash = bcrypt.generate_password_hash(password)
            user = User(
                name=nombre + " " + apellido,
                email=email,
                password=hash,
                role_id=1
            )
            code = random.randint(100000, 999999)
            email_send_verification(email,code)
            #TODO: make dashboard
            return render_template("email_verification.html",user=user,code=code) 
        
    return render_template('auth/signup.html')

@app.route('/auth/login/google')
def login_google():
    return render_template('auth/signup.html')

@app.route('/auth/signup/google')
def signup_google():
    return render_template('auth/signup.html')

@app.route('/auth/mail/verification', methods=["POST"])
def email_verification():
    code_form = request.form.get("code_email")
    code = request.form.get("code")
    user = request.form.get("user")
    if code == code_form and code and user and code_form:
        db.session.add(user)
        db.session.commit()
        flash("cliente creado exitosamente","success")
        return render_template("index.html")
    flash("el codigó no es correcto","warning")
    return render_template("email_verification.html",code=code,user=user)

def email_send_verification(email,code):
    msg = EmailMessage(
        subject="NotaLite",
        body=f"Verifica tu email ingresando el codigó:{code} para registrar",
        to=[email],
        from_email=os.getenv("MAIL_DEFAULT_SENDER"),
    )
    try:
        msg.send()
        flash("Correo electrónico enviado con éxito.", "success")
    except BadHeaderError:
        flash(
            "Encabezado no válido detectado. Posible intento de inyección de"
            " encabezados.",
            "danger",
        )
    except (ConnectionRefusedError, smtplib.SMTPException):
        flash(
            "No se pudo conectar con el servidor de correo. Inténtalo de"
            " nuevo más tarde.",
            "danger",
        )
    except Exception:
        flash("Ocurrió un error al enviar el correo.", "danger")

if __name__ == '__main__':
    app.run(debug=True)
