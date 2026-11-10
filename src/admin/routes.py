import os
from datetime import timedelta
from functools import wraps

from flask import abort, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from src.admin import bp
from src.extensions import db
from src.models import Note, User, utcnow
from src.notes.utils import sidebar_data
from src.services.storage import upload_root


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)

        return view(*args, **kwargs)

    return wrapped


def directory_size(path):
    total = 0

    for root, _directories, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue

    return total


def human_size(size):
    value = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} TB"


def as_utc(value, reference):
    if value and value.tzinfo is None:
        return value.replace(tzinfo=reference.tzinfo)

    return value


def weekly_activity(notes, weeks=8):
    now = utcnow()
    counts = []

    for offset in range(weeks - 1, -1, -1):
        start = now - timedelta(days=7 * (offset + 1))
        end = now - timedelta(days=7 * offset)
        counts.append(
            sum(
                1
                for note in notes
                if note.created_at and start <= as_utc(note.created_at, now) < end
            )
        )

    maximum = max(counts) or 1
    return [
        {
            "label": f"S{weeks - index}",
            "count": count,
            "height": max(6, round(count / maximum * 100)),
        }
        for index, count in enumerate(counts)
    ]


@bp.route("/")
@login_required
@admin_required
def dashboard():
    query = (request.args.get("q") or "").strip()
    users_query = User.query

    if query:
        pattern = f"%{query}%"
        users_query = users_query.filter(
            or_(User.name.ilike(pattern), User.email.ilike(pattern))
        )

    users = users_query.order_by(User.timestamp.desc()).limit(50).all()
    note_counts = dict(
        db.session.query(Note.user_id, func.count(Note.id))
        .filter(Note.to_delete == False)
        .group_by(Note.user_id)
        .all()
    )

    all_notes = Note.query.all()
    total_notes = sum(1 for note in all_notes if not note.to_delete)
    trashed_notes = len(all_notes) - total_notes
    cutoff = utcnow() - timedelta(days=30)
    active_user_ids = {
        note.user_id
        for note in all_notes
        if not note.to_delete
        and note.modified_at
        and as_utc(note.modified_at, cutoff) >= cutoff
    }
    total_users = User.query.count()

    stats = [
        {
            "label": "Usuarios totales",
            "value": total_users,
            "detail": f"{len(active_user_ids)} activos en 30 días",
        },
        {
            "label": "Notas activas",
            "value": total_notes,
            "detail": f"{trashed_notes} en papelera",
        },
        {
            "label": "Almacenamiento",
            "value": human_size(directory_size(upload_root())),
            "detail": "imágenes y adjuntos",
        },
        {
            "label": "Notas por usuario",
            "value": round(total_notes / max(1, total_users), 1),
            "detail": "promedio general",
        },
    ]

    return render_template(
        "admin/dashboard.html",
        users=users,
        recent_users=User.query.order_by(User.timestamp.desc()).limit(5).all(),
        note_counts=note_counts,
        stats=stats,
        activity=weekly_activity(all_notes),
        query=query,
        **sidebar_data(),
    )
