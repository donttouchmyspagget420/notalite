import os

from flask import Flask

from config import Config
from src.extensions import bcrypt, csrf, db, login_manager, mail

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app(config_object=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
        instance_path=os.path.join(BASE_DIR, "instance"),
    )
    app.config.from_object(config_object)

    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    from src.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from src.auth import bp as auth_bp
    from src.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from src import cli

    cli.init_app(app)


    return app
