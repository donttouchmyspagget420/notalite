import random

from flask import render_template
from flask_login import login_required

from src.notes import bp

@bp.route("/list")
@login_required
def list_notes():
    return render_template("notes/list.html")



