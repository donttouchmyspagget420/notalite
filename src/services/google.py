from src.extensions import oauth
from dotenv import load_dotenv
from flask import url_for
import os

load_dotenv()

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def getUserInfo():
    token = google.authorize_access_token()
    return token['userinfo']

def googleUri():
    return google.authorize_redirect(url_for("auth.callback_google", _external=True))
