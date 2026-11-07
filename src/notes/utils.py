import io
import re
import unicodedata
from datetime import datetime, timezone

from flask import abort, redirect, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import func

from src.enums import NoteLength, TimeUnit
from src.extensions import db
from src.models import Directory, Note, Tag, note_tags
from src.notes.exporters import build_pdf


def time_ago(value):
    if not value:
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    seconds = max(0, int((now - value).total_seconds()))

    if seconds < TimeUnit.MINUTE:
        return "hace instantes"
    if seconds < TimeUnit.HOUR:
        minutes = seconds // TimeUnit.MINUTE
        return f"hace {minutes} min"
    if seconds < TimeUnit.DAY:
        hours = seconds // TimeUnit.HOUR
        return f"hace {hours} h"
    if seconds < TimeUnit.TWO_DAYS:
        return "ayer"

    days = seconds // TimeUnit.DAY
    return f"hace {days} d"


def slugify(value, fallback="nota"):
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or fallback


def note_title_from_markdown(filename, content):
    for line in (content or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title[:NoteLength.TITLE]

    title = (filename or "").rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()
    return (title or "Nota importada")[:NoteLength.TITLE]


def active_notes():
    return Note.query.filter(Note.user_id == current_user.id, Note.to_delete == False)


def user_tags():
    return Tag.query.filter_by(user_id=current_user.id).order_by(func.lower(Tag.nombre))


def grouped_notes_by_directory():
    grouped = {}

    for note in active_notes().order_by(Note.modified_at.desc()).all():
        grouped.setdefault(note.directory_id, []).append(note)

    return grouped


def tag_or_404(tag_id):
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first()

    if not tag:
        abort(404)

    return tag


def directory_or_404(directory_id):
    directory = Directory.query.filter_by(
        id=directory_id, user_id=current_user.id
    ).first()

    if not directory:
        abort(404)

    return directory


def directory_or_none(directory_id):
    if not directory_id:
        return None

    try:
        directory_id = int(directory_id)
    except (TypeError, ValueError):
        return None

    return Directory.query.filter_by(
        id=directory_id, user_id=current_user.id
    ).first()


def directory_breadcrumbs(directory):
    breadcrumbs = []
    current = directory

    while current:
        breadcrumbs.append(current)
        current = current.parent

    return list(reversed(breadcrumbs))


def default_directory(exclude_id=None):
    query = Directory.query.filter_by(user_id=current_user.id)

    if exclude_id is not None:
        query = query.filter(Directory.id != exclude_id)

    directory = query.filter(func.lower(Directory.name) == "inbox").first()
    if directory:
        return directory

    directory = query.filter(Directory.parent_id.is_(None)).order_by(Directory.id).first()
    if directory:
        return directory

    directory = Directory(name="Inbox", user_id=current_user.id)
    db.session.add(directory)
    db.session.commit()
    return directory


def note_or_404(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()

    if not note:
        abort(404)

    return note


def safe_next(default_endpoint, **values):
    next_url = request.form.get("next") or request.args.get("next")

    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)

    return redirect(url_for(default_endpoint, **values))


def sidebar_data():
    directories = (
        Directory.query.filter_by(user_id=current_user.id)
        .order_by(func.lower(Directory.name))
        .all()
    )

    note_counts = dict(
        db.session.query(Note.directory_id, func.count(Note.id))
        .filter(Note.user_id == current_user.id, Note.to_delete == False)
        .group_by(Note.directory_id)
        .all()
    )

    tag_counts = dict(
        db.session.query(note_tags.c.tag_id, func.count(note_tags.c.note_id))
        .join(Note, Note.id == note_tags.c.note_id)
        .join(Tag, Tag.id == note_tags.c.tag_id)
        .filter(
            Note.user_id == current_user.id,
            Note.to_delete == False,
            Tag.user_id == current_user.id,
        )
        .group_by(note_tags.c.tag_id)
        .all()
    )

    tags = user_tags().all()
    total_notes = Note.query.filter(
        Note.user_id == current_user.id, Note.to_delete == False
    ).count()

    name_parts = (current_user.name or "").split()
    initials = "".join(part[0] for part in name_parts[:2]).upper()

    if not initials:
        initials = (current_user.email or "?")[0].upper()

    return {
        "sidebar_directories": directories,
        "directory_roots": [directory for directory in directories if not directory.parent_id],
        "directory_note_counts": note_counts,
        "sidebar_tags": [(tag, tag_counts.get(tag.id, 0)) for tag in tags],
        "total_notes": total_notes,
        "user_initials": initials,
    }


def export_response(note, export_format):
    if export_format not in {"md", "pdf"}:
        abort(404)

    base_name = slugify(note.title, fallback="nota")

    if export_format == "md":
        content = note.content or ""

        if not content.lstrip().startswith("#"):
            content = f"# {note.title}\n\n{content}"

        return send_file(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/markdown",
            as_attachment=True,
            download_name=f"{base_name}.md",
        )

    pdf = build_pdf(note.title, note.content)
    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{base_name}.pdf",
    )
