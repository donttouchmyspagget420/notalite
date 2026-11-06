from flask import Blueprint

bp = Blueprint("notes", __name__)

from src.notes import routes  
