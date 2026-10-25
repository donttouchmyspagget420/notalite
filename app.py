from flask import Flask, render_template, request, session, flash
from flask_bcrypt import Bcrypt, check_password_hash
from flask_login import LoginManager, login_user
from flask_wtf import CSRFProtect
from models import db,User
from dotenv import load_dotenv
from flask_mailman import Mail
import os

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app);
login_manager = LoginManager(app)
mail = Mail(app)

app.secret_key = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")

db.init_app(app)

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
            flash("all fields are required")
        else:
            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                session["username"] = user.username
                return render_template("index.html")

            flash("wrong password or login")
        
    return render_template('auth/login.html')

@app.route('/auth/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        nombre = request.form["name"]
        apellido = request.form["surname"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not username and not email and not password and not confirm_password:
            flash("all fields are require")
        elif User.query.filter_by(username=username).first():
            flash("user already exists")
        elif password != confirm_password:
            flash("passwords have to match")
        else:
            hash = bcrypt.generate_password_hash(password)
            db.session.add(User(
                username=username,
                name = nombre + " " + apellido,
                email=email,
                password=hash,
                role_id=1
            ))
            db.session.commit()
            flash("User created")
            #TODO: make dashboard
            return render_template("index.html") 
        
    return render_template('auth/signup.html')

@app.route('/auth/login/google')
def login_google():
    return render_template('auth/signup.html')

@app.route('/auth/signup/google')
def signup_google():
    return render_template('auth/signup.html')

@app.route('/auth/mail/verification')
def mail_verification():
    return render_template('auth/signup.html')


if __name__ == '__main__':
    app.run(debug=True)
