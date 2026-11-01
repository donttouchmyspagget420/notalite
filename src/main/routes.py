from flask import render_template

from src.main import bp


@bp.route("/")
def root():
    return render_template("index.html")
