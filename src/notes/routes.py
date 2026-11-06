import io

from flask import (
    abort,
    flash,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from src.extensions import db
from src.models import Directory, Note, Tag, note_tags, utcnow
from src.notes import bp
from src.notes.exporters import build_pdf
from src.notes.utils import note_title_from_markdown, slugify, time_ago


MAX_IMPORT_FILES = 10
MAX_IMPORT_BYTES = 25 * 1024 * 1024
TAG_COLORS = ["#60a5fa", "#fbbf24", "#34d399", "#f87171", "#8b5cf6", "#ec4899"]

NOTE_TEMPLATES = {
    "blank": ("Nota sin título", ""),
    "template": (
        "Nueva nota desde plantilla",
        "## Objetivo\n\n- \n\n## Notas\n\n- \n\n## Próximos pasos\n\n- \n",
    ),
    "wiki": ("Nota desde wiki-link", "[[Concepto]]\n\n"),
}


bp.add_app_template_filter(time_ago, "timeago")


@bp.app_context_processor
def inject_sidebar_data():
    if not has_request_context() or not current_user.is_authenticated:
        return {
            "sidebar_directories": [],
            "directory_roots": [],
            "directory_note_counts": {},
            "sidebar_tags": [],
            "total_notes": 0,
            "user_initials": "",
        }

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
        .filter(Note.user_id == current_user.id, Note.to_delete == False)
        .group_by(note_tags.c.tag_id)
        .all()
    )

    tags = Tag.query.order_by(func.lower(Tag.nombre)).all()
    total_notes = (
        Note.query.filter(Note.user_id == current_user.id, Note.to_delete == False).count()
    )

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


def _active_notes():
    return Note.query.filter(Note.user_id == current_user.id, Note.to_delete == False)


def _directory_or_404(directory_id):
    directory = Directory.query.filter_by(
        id=directory_id, user_id=current_user.id
    ).first()
    if not directory:
        abort(404)
    return directory


def _directory_or_none(directory_id):
    if not directory_id:
        return None
    try:
        directory_id = int(directory_id)
    except (TypeError, ValueError):
        return None
    return Directory.query.filter_by(
        id=directory_id, user_id=current_user.id
    ).first()


def _default_directory(exclude_id=None):
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


def _note_or_404(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
    if not note:
        abort(404)
    return note


def _safe_next(default_endpoint, **values):
    next_url = request.form.get("next") or request.args.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(url_for(default_endpoint, **values))


def _tag_color(name):
    return TAG_COLORS[sum(ord(character) for character in name) % len(TAG_COLORS)]


def _export_response(note, export_format):
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


@bp.route("/list")
@login_required
def list_notes():
    notes = _active_notes().order_by(Note.modified_at.desc()).all()
    return render_template("notes/list.html", notes=notes)


@bp.route("/create", methods=["POST"])
@login_required
def create_note():
    mode = request.form.get("mode", "blank").strip()
    default_title, default_content = NOTE_TEMPLATES.get(mode, NOTE_TEMPLATES["blank"])

    title = request.form.get("title", "").strip() or default_title
    content = request.form.get("content")
    if content is None:
        content = default_content

    directory = _directory_or_none(request.form.get("directory_id"))
    if not directory:
        directory = _default_directory()

    now = utcnow()
    note = Note(
        title=title[:255],
        name=f"{slugify(title, fallback='nota')[:90]}.md",
        content=content,
        created_at=now,
        modified_at=now,
        to_delete=False,
        user_id=current_user.id,
        directory_id=directory.id,
    )

    db.session.add(note)
    db.session.commit()

    flash("Nota creada.", "success")
    return redirect(url_for("notes.edit_note", note_id=note.id))


@bp.route("/<int:note_id>")
@login_required
def edit_note(note_id):
    note = _note_or_404(note_id)
    note_tag_ids = {tag.id for tag in note.tags}
    return render_template(
        "notes/editor.html",
        note=note,
        note_tag_ids=note_tag_ids,
        word_count=len((note.content or "").split()),
    )


@bp.route("/<int:note_id>/save", methods=["POST"])
@login_required
def save_note(note_id):
    note = _note_or_404(note_id)
    payload = request.get_json(silent=True) or request.form

    title = (payload.get("title") or note.title or "Nota sin título").strip()
    content = payload.get("content", note.content)
    if content is None:
        content = ""

    note.title = title[:255]
    note.content = str(content)
    note.modified_at = utcnow()
    db.session.commit()

    return jsonify(
        ok=True,
        title=note.title,
        words=len(note.content.split()),
        saved_at=note.modified_at.strftime("%H:%M"),
    )


@bp.route("/<int:note_id>/tags", methods=["POST"])
@login_required
def update_note_tags(note_id):
    note = _note_or_404(note_id)

    tag_ids = []
    for value in request.form.getlist("tag_ids"):
        try:
            tag_ids.append(int(value))
        except (TypeError, ValueError):
            continue

    tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
    note.tags = tags
    note.modified_at = utcnow()
    db.session.commit()

    flash("Etiquetas actualizadas.", "success")
    return _safe_next("notes.edit_note", note_id=note.id)


@bp.route("/<int:note_id>/tags/<int:tag_id>/remove", methods=["POST"])
@login_required
def remove_note_tag(note_id, tag_id):
    note = _note_or_404(note_id)
    tag = db.get_or_404(Tag, tag_id)

    if tag in note.tags:
        note.tags.remove(tag)
        note.modified_at = utcnow()
        db.session.commit()
        flash(f"Etiqueta #{tag.nombre} quitada de la nota.", "success")

    return _safe_next("notes.tags", tag_id=tag.id)


@bp.route("/<int:note_id>/move", methods=["POST"])
@login_required
def move_note(note_id):
    note = _note_or_404(note_id)
    directory = _directory_or_none(request.form.get("directory_id"))

    if not directory:
        flash("Elegí una carpeta válida.", "warning")
        return _safe_next("notes.list_notes")

    note.directory_id = directory.id
    note.modified_at = utcnow()
    db.session.commit()

    flash(f"Nota movida a «{directory.name}».", "success")
    return _safe_next("notes.folders", directory_id=directory.id)


@bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = _note_or_404(note_id)
    note.to_delete = True
    note.deleted_at = utcnow()
    db.session.commit()

    flash("Nota movida a la papelera.", "success")
    return _safe_next("notes.list_notes")


@bp.route("/<int:note_id>/export/<string:export_format>")
@login_required
def export_note(note_id, export_format):
    note = _note_or_404(note_id)
    return _export_response(note, export_format)


@bp.route("/folders")
@bp.route("/folders/<int:directory_id>")
@login_required
def folders(directory_id=None):
    if directory_id is None:
        directory = (
            Directory.query.filter_by(user_id=current_user.id, parent_id=None)
            .order_by(Directory.id)
            .first()
        )
        if not directory:
            directory = _default_directory()
    else:
        directory = _directory_or_404(directory_id)

    notes = (
        _active_notes()
        .filter(Note.directory_id == directory.id)
        .order_by(Note.modified_at.desc())
        .all()
    )

    return render_template(
        "folders/index.html",
        active_directory=directory,
        notes=notes,
    )


@bp.route("/folders/create", methods=["POST"])
@login_required
def create_folder():
    name = request.form.get("name", "").strip()
    parent = _directory_or_none(request.form.get("parent_id"))

    if not name:
        flash("El nombre de la carpeta es obligatorio.", "warning")
        return _safe_next("notes.folders")

    directory = Directory(
        name=name[:100],
        user_id=current_user.id,
        parent_id=parent.id if parent else None,
    )
    db.session.add(directory)
    db.session.commit()

    flash("Carpeta creada.", "success")
    return redirect(url_for("notes.folders", directory_id=directory.id))


@bp.route("/folders/<int:directory_id>/rename", methods=["POST"])
@login_required
def rename_folder(directory_id):
    directory = _directory_or_404(directory_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("El nombre de la carpeta es obligatorio.", "warning")
    else:
        directory.name = name[:100]
        db.session.commit()
        flash("Carpeta renombrada.", "success")

    return _safe_next("notes.folders", directory_id=directory.id)


@bp.route("/folders/<int:directory_id>/delete", methods=["POST"])
@login_required
def delete_folder(directory_id):
    directory = _directory_or_404(directory_id)

    fallback = directory.parent or _default_directory(exclude_id=directory.id)
    Note.query.filter_by(user_id=current_user.id, directory_id=directory.id).update(
        {Note.directory_id: fallback.id}, synchronize_session=False
    )

    for child in list(directory.children):
        child.parent_id = directory.parent_id

    db.session.delete(directory)
    db.session.commit()

    flash("Carpeta eliminada; sus notas se movieron a "
          f"«{fallback.name}».", "success")
    return redirect(url_for("notes.folders", directory_id=fallback.id))


@bp.route("/tags")
@bp.route("/tags/<int:tag_id>")
@login_required
def tags(tag_id=None):
    all_tags = Tag.query.order_by(func.lower(Tag.nombre)).all()

    if tag_id is not None:
        tag = db.get_or_404(Tag, tag_id)
    else:
        tag = all_tags[0] if all_tags else None

    notes = []
    if tag:
        note_ids = db.session.query(note_tags.c.note_id).filter(
            note_tags.c.tag_id == tag.id
        )
        notes = (
            _active_notes()
            .filter(Note.id.in_(note_ids))
            .order_by(Note.modified_at.desc())
            .all()
        )

    return render_template(
        "tags/index.html",
        active_tag=tag,
        notes=notes,
        all_tags=all_tags,
    )


@bp.route("/tags/create", methods=["POST"])
@login_required
def create_tag():
    name = request.form.get("name", "").strip().lstrip("#")
    if not name:
        flash("El nombre de la etiqueta es obligatorio.", "warning")
        return _safe_next("notes.tags")

    existing = Tag.query.filter(func.lower(Tag.nombre) == name.lower()).first()
    if existing:
        flash(f"La etiqueta #{existing.nombre} ya existe.", "info")
        return redirect(url_for("notes.tags", tag_id=existing.id))

    tag = Tag(nombre=name[:100], color=_tag_color(name))
    db.session.add(tag)
    db.session.commit()

    flash(f"Etiqueta #{tag.nombre} creada.", "success")
    return redirect(url_for("notes.tags", tag_id=tag.id))


@bp.route("/tags/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_tag(tag_id):
    tag = db.get_or_404(Tag, tag_id)

    for note in list(tag.notes):
        note.tags.remove(tag)

    db.session.delete(tag)
    db.session.commit()

    flash(f"Etiqueta #{tag.nombre} eliminada de todas las notas.", "success")
    return redirect(url_for("notes.tags"))


@bp.route("/import-export")
@login_required
def import_export():
    notes = _active_notes().order_by(Note.modified_at.desc()).all()
    return render_template(
        "settings/import_export.html",
        notes=notes,
        active_note=notes[0] if notes else None,
    )


@bp.route("/export", methods=["POST"])
@login_required
def export_selected():
    note = _note_or_404(request.form.get("note_id", type=int))
    return _export_response(note, request.form.get("format", "md"))


@bp.route("/import", methods=["POST"])
@login_required
def import_notes():
    files = [file for file in request.files.getlist("files") if file and file.filename]

    if not files:
        flash("Elegí al menos un archivo .md.", "warning")
        return redirect(url_for("notes.import_export"))

    directory = _directory_or_none(request.form.get("directory_id"))
    if not directory:
        directory = _default_directory()

    imported = 0
    skipped = 0

    for file in files[:MAX_IMPORT_FILES]:
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(".md"):
            skipped += 1
            continue

        raw = file.read(MAX_IMPORT_BYTES + 1)
        if len(raw) > MAX_IMPORT_BYTES:
            skipped += 1
            continue

        content = raw.decode("utf-8", errors="replace")
        exists = Note.query.filter_by(
            user_id=current_user.id,
            name=filename,
            to_delete=False,
        ).first()
        if exists:
            skipped += 1
            continue

        title = note_title_from_markdown(filename, content)
        now = utcnow()
        note = Note(
            title=title,
            name=filename[:100],
            content=content,
            created_at=now,
            modified_at=now,
            to_delete=False,
            user_id=current_user.id,
            directory_id=directory.id,
        )
        db.session.add(note)
        imported += 1

    db.session.commit()

    category = "success" if imported else "warning"
    flash(
        f"{imported} nota(s) importada(s). {skipped} archivo(s) omitido(s).",
        category,
    )
    return redirect(url_for("notes.import_export"))
