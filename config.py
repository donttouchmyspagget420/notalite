import os

from dotenv import load_dotenv

load_dotenv()


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = env_bool("SQLALCHEMY_TRACK_MODIFICATIONS")
    MAIL_BACKEND = os.getenv("MAIL_BACKEND")
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT")
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS")
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    GOOGLE_LLM_API_KEY = os.getenv("GOOGLE_LLM_API_KEY")
    GOOGLE_LLM_MODEL = os.getenv("GOOGLE_LLM_MODEL")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")

    # Image storage: "local" (default) or "s3".
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
    AWS_S3_PREFIX = os.getenv("AWS_S3_PREFIX")
    AWS_S3_PUBLIC_URL = os.getenv("AWS_S3_PUBLIC_URL")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_S3_ACL = os.getenv("AWS_S3_ACL")
