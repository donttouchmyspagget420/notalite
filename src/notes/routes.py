from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from src.enums import ImportLimit, NoteLength
from src.extensions import db
from src.models import Directory, Note, Tag, note_tags, utcnow
from src.notes import bp
from src.notes.utils import (
    active_notes,
    default_directory,
    directory_breadcrumbs,
    directory_or_404,
    directory_or_none,
    export_response,
    grouped_notes_by_directory,
    note_or_404,
    note_title_from_markdown,
    safe_next,
    sidebar_data,
    slugify,
    tag_or_404,
    time_ago,
    user_tags,
)


bp.add_app_template_filter(time_ago, "timeago")


@bp.route("/list")
@login_required
def list_notes():
    notes = active_notes().order_by(Note.modified_at.desc()).all()
    return render_template("notes/list.html", notes=notes, **sidebar_data())


@bp.route("/create", methods=["POST"])
@login_required
def create_note():
    note_templates = {
        "blank": ("Nota sin título", ""),
        "template": (
            "Nueva nota desde plantilla",
            "## Objetivo\n\n- \n\n## Notas\n\n- \n\n## Próximos pasos\n\n- \n",
        ),
        "wiki": ("Nota desde wiki-link", "[[Concepto]]\n\n"),
    }

    mode = request.form.get("mode", "blank").strip()
    default_title, default_content = note_templates.get(mode, note_templates["blank"])

    title = request.form.get("title", "").strip() or default_title
    content = request.form.get("content")

    if content is None:
        content = default_content

    directory = directory_or_none(request.form.get("directory_id"))

    if not directory:
        directory = default_directory()

    now = utcnow()
    note = Note(
        title=title[:NoteLength.TITLE],
        name=f"{slugify(title, fallback='nota')[:NoteLength.SLUG]}.md",
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
    return safe_next("notes.edit_note", note_id=note.id)


@bp.route("/<int:note_id>")
@login_required
def edit_note(note_id):
    note = note_or_404(note_id)
    note_tag_ids = {tag.id for tag in note.tags}

    return render_template(
        "notes/editor.html",
        note=note,
        note_tag_ids=note_tag_ids,
        word_count=len((note.content or "").split()),
        **sidebar_data(),
    )


@bp.route("/<int:note_id>/save", methods=["POST"])
@login_required
def save_note(note_id):
    note = note_or_404(note_id)
    payload = request.get_json(silent=True) or request.form

    title = (payload.get("title") or note.title or "Nota sin título").strip()
    content = payload.get("content", note.content)

    if content is None:
        content = ""

    note.title = title[:NoteLength.TITLE]
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
    note = note_or_404(note_id)
    tag_ids = []

    for value in request.form.getlist("tag_ids"):
        try:
            tag_ids.append(int(value))
        except (TypeError, ValueError):
            continue

    tags = (
        user_tags().filter(Tag.id.in_(tag_ids)).all()
        if tag_ids
        else []
    )
    note.tags = tags
    note.modified_at = utcnow()
    db.session.commit()

    flash("Etiquetas actualizadas.", "success")
    return safe_next("notes.edit_note", note_id=note.id)


@bp.route("/<int:note_id>/tags/<int:tag_id>/remove", methods=["POST"])
@login_required
def remove_note_tag(note_id, tag_id):
    note = note_or_404(note_id)
    tag = tag_or_404(tag_id)

    if tag in note.tags:
        note.tags.remove(tag)
        note.modified_at = utcnow()
        db.session.commit()
        flash(f"Etiqueta #{tag.nombre} quitada de la nota.", "success")

    return safe_next("notes.tags", tag_id=tag.id)


@bp.route("/<int:note_id>/move", methods=["POST"])
@login_required
def move_note(note_id):
    note = note_or_404(note_id)
    directory = directory_or_none(request.form.get("directory_id"))

    if not directory:
        flash("Elegí una carpeta válida.", "warning")
        return safe_next("notes.list_notes")

    note.directory_id = directory.id
    note.modified_at = utcnow()
    db.session.commit()

    flash(f"Nota movida a «{directory.name}».", "success")
    return safe_next("notes.folders", directory_id=directory.id)


@bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = note_or_404(note_id)
    note.to_delete = True
    note.deleted_at = utcnow()
    db.session.commit()

    flash("Nota movida a la papelera.", "success")
    return safe_next("notes.list_notes")


@bp.route("/<int:note_id>/export/<string:export_format>")
@login_required
def export_note(note_id, export_format):
    note = note_or_404(note_id)
    return export_response(note, export_format)


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
            directory = default_directory()
    else:
        directory = directory_or_404(directory_id)

    notes_by_directory = grouped_notes_by_directory()
    notes = notes_by_directory.get(directory.id, [])
    subfolders = sorted(
        [child for child in directory.children if child.user_id == current_user.id],
        key=lambda child: child.name.lower(),
    )

    return render_template(
        "folders/index.html",
        active_directory=directory,
        breadcrumbs=directory_breadcrumbs(directory),
        subfolders=subfolders,
        notes=notes,
        **sidebar_data(),
    )


@bp.route("/folders/tree")
@login_required
def folders_tree():
    return render_template(
        "folders/tree.html",
        notes_by_directory=grouped_notes_by_directory(),
        **sidebar_data(),
    )


@bp.route("/folders/create", methods=["POST"])
@login_required
def create_folder():
    name = request.form.get("name", "").strip()
    parent = directory_or_none(request.form.get("parent_id"))

    if not name:
        flash("El nombre de la carpeta es obligatorio.", "warning")
        return safe_next("notes.folders")

    directory = Directory(
        name=name[:NoteLength.NAME],
        user_id=current_user.id,
        parent_id=parent.id if parent else None,
    )

    db.session.add(directory)
    db.session.commit()

    flash("Carpeta creada.", "success")
    return safe_next("notes.folders", directory_id=directory.id)


@bp.route("/folders/<int:directory_id>/rename", methods=["POST"])
@login_required
def rename_folder(directory_id):
    directory = directory_or_404(directory_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("El nombre de la carpeta es obligatorio.", "warning")
    else:
        directory.name = name[:NoteLength.NAME]
        db.session.commit()
        flash("Carpeta renombrada.", "success")

    return safe_next("notes.folders", directory_id=directory.id)


@bp.route("/folders/<int:directory_id>/delete", methods=["POST"])
@login_required
def delete_folder(directory_id):
    directory = directory_or_404(directory_id)
    fallback = directory.parent or default_directory(exclude_id=directory.id)

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
    all_tags = user_tags().all()

    if tag_id is not None:
        tag = tag_or_404(tag_id)
    else:
        tag = all_tags[0] if all_tags else None

    notes = []

    if tag:
        note_ids = db.session.query(note_tags.c.note_id).filter(
            note_tags.c.tag_id == tag.id
        )
        notes = (
            active_notes()
            .filter(Note.id.in_(note_ids))
            .order_by(Note.modified_at.desc())
            .all()
        )

    return render_template(
        "tags/index.html",
        active_tag=tag,
        notes=notes,
        all_tags=all_tags,
        **sidebar_data(),
    )


@bp.route("/tags/create", methods=["POST"])
@login_required
def create_tag():
    name = request.form.get("name", "").strip().lstrip("#")

    if not name:
        flash("El nombre de la etiqueta es obligatorio.", "warning")
        return safe_next("notes.tags")

    existing = user_tags().filter(func.lower(Tag.nombre) == name.lower()).first()

    if existing:
        flash(f"La etiqueta #{existing.nombre} ya existe.", "info")
        return redirect(url_for("notes.tags", tag_id=existing.id))

    tag = Tag(
        nombre=name[:NoteLength.NAME],
        user_id=current_user.id,
    )

    db.session.add(tag)
    db.session.commit()

    flash(f"Etiqueta #{tag.nombre} creada.", "success")
    return redirect(url_for("notes.tags", tag_id=tag.id))


@bp.route("/tags/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_tag(tag_id):
    tag = tag_or_404(tag_id)

    for note in list(tag.notes):
        note.tags.remove(tag)

    db.session.delete(tag)
    db.session.commit()

    flash(f"Etiqueta #{tag.nombre} eliminada de todas las notas.", "success")
    return redirect(url_for("notes.tags"))


@bp.route("/import-export")
@login_required
def import_export():
    notes = active_notes().order_by(Note.modified_at.desc()).all()

    return render_template(
        "settings/import_export.html",
        notes=notes,
        active_note=notes[0] if notes else None,
        **sidebar_data(),
    )


@bp.route("/export", methods=["POST"])
@login_required
def export_selected():
    note = note_or_404(request.form.get("note_id", type=int))
    return export_response(note, request.form.get("format", "md"))


@bp.route("/import", methods=["POST"])
@login_required
def import_notes():
    files = [file for file in request.files.getlist("files") if file and file.filename]

    if not files:
        flash("Elegí al menos un archivo .md.", "warning")
        return redirect(url_for("notes.import_export"))

    directory = directory_or_none(request.form.get("directory_id"))

    if not directory:
        directory = default_directory()

    imported = 0
    skipped = 0

    for file in files[:ImportLimit.FILES]:
        filename = secure_filename(file.filename)

        if not filename.lower().endswith(".md"):
            skipped += 1
            continue

        raw = file.read(ImportLimit.BYTES + 1)

        if len(raw) > ImportLimit.BYTES:
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
            name=filename[:NoteLength.NAME],
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
