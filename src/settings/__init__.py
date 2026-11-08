from flask import Blueprint

bp = Blueprint("settings", __name__)

from src.settings import routes
