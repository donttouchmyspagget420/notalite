from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mailman import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
bcrypt = Bcrypt()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()
