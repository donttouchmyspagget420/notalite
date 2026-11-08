import os

from flask import Flask

from config import Config
from src.extensions import bcrypt, csrf, db, login_manager, mail, oauth
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app(config_object=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
        instance_path=os.path.join(BASE_DIR, "instance"),
    )
    app.config.from_object(config_object)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    oauth.init_app(app)

    from src.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from src.auth import bp as auth_bp
    from src.main import bp as main_bp
    from src.notes import bp as notes_bp
    from src.settings import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(notes_bp, url_prefix="/notes")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    from src import cli

    cli.init_app(app)


    return app
