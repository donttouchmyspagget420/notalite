from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mailman import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
bcrypt = Bcrypt()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()
oauth = OAuth()
