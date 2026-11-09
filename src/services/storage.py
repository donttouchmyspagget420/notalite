"""Image storage backends.

Images are stored locally by default. Set ``STORAGE_BACKEND=s3`` (or configure
an ``AWS_S3_BUCKET``) to store them in Amazon S3 or any S3-compatible service.
"""

import mimetypes
import os
import uuid

from flask import current_app, url_for
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "gif", "webp")


class StorageError(Exception):
    pass


def upload_root():
    configured = current_app.config.get("UPLOAD_FOLDER") or "storage"

    if os.path.isabs(configured):
        return configured

    project_root = os.path.dirname(current_app.root_path)
    return os.path.join(project_root, configured)


def _extension(filename):
    cleaned = secure_filename(filename or "")
    extension = cleaned.rsplit(".", 1)[-1].lower() if "." in cleaned else ""

    if extension not in IMAGE_EXTENSIONS:
        raise StorageError(
            "Formato no permitido. Usá PNG, JPG, GIF o WebP."
        )

    return extension


def _backend():
    configured = (current_app.config.get("STORAGE_BACKEND") or "").strip().lower()

    if configured in {"s3", "aws"}:
        return "s3"
    if configured == "local":
        return "local"

    return "s3" if current_app.config.get("AWS_S3_BUCKET") else "local"


def _save_local(upload, key):
    destination = os.path.join(upload_root(), *key.split("/"))
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    upload.save(destination)

    return url_for("notes.uploaded_image", filename=key)


def _s3_client():
    try:
        import boto3
    except ImportError as error:
        raise StorageError(
            "El almacenamiento S3 requiere boto3. Ejecutá "
            "«pip install -r requirements.txt»."
        ) from error

    client_kwargs = {
        "aws_access_key_id": current_app.config.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": current_app.config.get("AWS_SECRET_ACCESS_KEY"),
        "region_name": current_app.config.get("AWS_REGION")
        or current_app.config.get("AWS_DEFAULT_REGION"),
    }

    endpoint = current_app.config.get("AWS_S3_ENDPOINT_URL")
    if endpoint:
        client_kwargs["endpoint_url"] = endpoint

    return boto3.client("s3", **client_kwargs)


def _save_s3(upload, key, extension):
    bucket = current_app.config.get("AWS_S3_BUCKET")

    if not bucket:
        raise StorageError(
            "Falta configurar AWS_S3_BUCKET para guardar imágenes en S3."
        )

    prefix = (current_app.config.get("AWS_S3_PREFIX") or "").strip("/")
    object_key = f"{prefix}/{key}" if prefix else key
    content_type = mimetypes.guess_type(f"image.{extension}")[0] or "application/octet-stream"

    extra_args = {"ContentType": content_type}
    acl = current_app.config.get("AWS_S3_ACL")
    if acl:
        extra_args["ACL"] = acl

    try:
        _s3_client().upload_fileobj(
            upload.stream,
            bucket,
            object_key,
            ExtraArgs=extra_args,
        )
    except StorageError:
        raise
    except Exception as error:
        raise StorageError("No se pudo subir la imagen a S3.") from error

    public_base = (current_app.config.get("AWS_S3_PUBLIC_URL") or "").strip()
    if public_base:
        return f"{public_base.rstrip('/')}/{object_key}"

    endpoint = (current_app.config.get("AWS_S3_ENDPOINT_URL") or "").strip()
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{object_key}"

    region = (
        current_app.config.get("AWS_REGION")
        or current_app.config.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )
    return f"https://{bucket}.s3.{region}.amazonaws.com/{object_key}"


def save_image(upload, user_id):
    """Persist an uploaded image and return its public URL."""
    if not upload or not upload.filename:
        raise StorageError("Elegí una imagen para subir.")

    extension = _extension(upload.filename)
    key = f"notes/{user_id}/{uuid.uuid4().hex}.{extension}"

    if _backend() == "s3":
        return _save_s3(upload, key, extension)

    return _save_local(upload, key)
