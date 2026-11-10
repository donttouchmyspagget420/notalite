import html
import io
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import func, or_

from src.enums import NoteLength, SearchLimit, TimeUnit, TrashRetention
from src.extensions import db
from src.models import Collab, Directory, Note, Tag, note_tags, utcnow
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


def ensure_utc(value):
    if value and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def highlight_text(value, query):
    """Escape a text and wrap every case-insensitive match in ``<mark>``."""
    escaped = html.escape(value or "")

    if not query:
        return escaped

    pattern = re.compile(re.escape(html.escape(query)), re.IGNORECASE)
    return pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", escaped)


def search_snippet(content, query):
    """Return a short, safe excerpt around the first match."""
    text = re.sub(r"\s+", " ", content or "").strip()

    if not text:
        return ""

    limit = int(SearchLimit.SNIPPET)
    match = re.search(re.escape(query), text, re.IGNORECASE) if query else None

    if match:
        start = max(0, match.start() - limit // 3)
        end = min(len(text), start + limit)
        start = max(0, end - limit)
    else:
        start = 0
        end = min(len(text), limit)

    snippet = text[start:end]
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""

    return f"{prefix}{highlight_text(snippet, query)}{suffix}"


def note_thumbnail(note):
    """Return the first image URL embedded in a note, if any."""
    content = note.content or ""

    patterns = (
        r"!\[[^\]]*\]\(\s*((?:https?://|/)[^)\s]+)",
        r"<img[^>]+src=[\"']((?:https?://|/)[^\"']+)[\"']",
    )

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            return match.group(1)

    return None


def trash_days_left(note):
    deleted_at = ensure_utc(note.deleted_at)

    if not deleted_at:
        return TrashRetention.DAYS

    elapsed = max(0, (utcnow() - deleted_at).total_seconds())
    remaining = TrashRetention.DAYS - int(elapsed // TimeUnit.DAY)
    return max(0, remaining)


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


def shared_with_me():
    return (
        Note.query.join(Collab, Collab.note_id == Note.id)
        .filter(Collab.user_id == current_user.id, Note.to_delete == False)
        .order_by(Note.modified_at.desc())
    )


def searchable_notes():
    shared_ids = db.session.query(Collab.note_id).filter(
        Collab.user_id == current_user.id
    )

    return Note.query.filter(
        Note.to_delete == False,
        or_(Note.user_id == current_user.id, Note.id.in_(shared_ids)),
    )


def search_notes(query, field="all"):
    query = (query or "").strip()

    if not query:
        return []

    pattern = f"%{query}%"
    notes = searchable_notes()

    if field == "title":
        notes = notes.filter(Note.title.ilike(pattern))
    elif field == "content":
        notes = notes.filter(Note.content.ilike(pattern))
    elif field == "tag":
        notes = notes.filter(Note.tags.any(Tag.nombre.ilike(pattern)))
    else:
        notes = notes.filter(
            or_(
                Note.title.ilike(pattern),
                Note.content.ilike(pattern),
                Note.tags.any(Tag.nombre.ilike(pattern)),
            )
        )

    return notes.order_by(Note.modified_at.desc()).limit(SearchLimit.RESULTS).all()


def trash_notes():
    return (
        Note.query.filter(Note.user_id == current_user.id, Note.to_delete == True)
        .order_by(Note.deleted_at.desc())
    )


def purge_expired_trash():
    cutoff = utcnow() - timedelta(days=TrashRetention.DAYS)
    expired = [
        note
        for note in trash_notes().all()
        if note.deleted_at and ensure_utc(note.deleted_at) <= cutoff
    ]

    for note in expired:
        db.session.delete(note)

    if expired:
        db.session.commit()

    return len(expired)


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


def note_owner_or_404(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()

    if not note:
        abort(404)

    return note


def note_or_404(note_id):
    """Kept for owner-only actions such as moving or deleting a note."""
    return note_owner_or_404(note_id)


def note_for_access(note_id, write=False):
    """Return a note visible to the current user and whether it is editable.

    Owners always have full access. Collaborators get read access and, when
    their permission is ``edit``, write access as well.
    """
    note = Note.query.filter_by(id=note_id).first()

    if not note:
        abort(404)

    if note.user_id == current_user.id:
        return note, True

    collab = Collab.query.filter_by(
        note_id=note.id, user_id=current_user.id
    ).first()

    if not collab:
        abort(404)

    can_edit = collab.permission == "edit"

    if write and not can_edit:
        abort(403)

    return note, can_edit


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
    shared_count = shared_with_me().count()
    trash_count = Note.query.filter(
        Note.user_id == current_user.id, Note.to_delete == True
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
        "shared_count": shared_count,
        "trash_count": trash_count,
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
