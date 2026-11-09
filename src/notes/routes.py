from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from src.enums import ImportLimit, NoteLength
from src.extensions import db
from src.services.forms import (
    FolderForm,
    ImageUploadForm,
    MoveNoteForm,
    ShareNoteForm,
    TagForm,
    form_error,
)
from src.services.gemini import LlmError, generate_text
from src.services.storage import StorageError, save_image, upload_root
from src.models import Collab, Directory, Note, Tag, User, note_tags, utcnow
from src.notes import bp
from src.notes.utils import (
    active_notes,
    directory_breadcrumbs,
    directory_or_404,
    directory_or_none,
    export_response,
    grouped_notes_by_directory,
    note_for_access,
    note_or_404,
    note_owner_or_404,
    note_title_from_markdown,
    safe_next,
    shared_with_me,
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


@bp.route("/shared")
@login_required
def shared_notes():
    notes = shared_with_me().all()
    permissions = {
        collab.note_id: collab.permission
        for collab in Collab.query.filter_by(user_id=current_user.id).all()
    }
    return render_template(
        "notes/shared.html",
        notes=notes,
        permissions=permissions,
        **sidebar_data(),
    )


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

    now = utcnow()
    note = Note(
        title=title[:NoteLength.TITLE],
        name=f"{slugify(title, fallback='nota')[:NoteLength.SLUG]}.md",
        content=content,
        created_at=now,
        modified_at=now,
        to_delete=False,
        user_id=current_user.id,
        directory_id=directory.id if directory else None,
    )

    db.session.add(note)
    db.session.commit()

    flash("Nota creada.", "success")
    return safe_next("notes.edit_note", note_id=note.id)


@bp.route("/<int:note_id>")
@login_required
def edit_note(note_id):
    note, can_edit = note_for_access(note_id)
    note_tag_ids = {tag.id for tag in note.tags}
    is_owner = note.user_id == current_user.id

    return render_template(
        "notes/editor.html",
        note=note,
        can_edit=can_edit,
        is_owner=is_owner,
        note_tag_ids=note_tag_ids,
        word_count=len((note.content or "").split()),
        **sidebar_data(),
    )


@bp.route("/<int:note_id>/save", methods=["POST"])
@login_required
def save_note(note_id):
    note, _ = note_for_access(note_id, write=True)
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


@bp.route("/<int:note_id>/ai", methods=["POST"])
@login_required
def ai_assist(note_id):
    note, _ = note_for_access(note_id, write=True)
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        payload = request.form

    action = (payload.get("action") or "improve").strip()
    selection = (payload.get("selection") or "").strip()
    instruction = (payload.get("prompt") or "").strip()
    source = selection or (note.content or "").strip()

    if not source:
        return jsonify(ok=False, error="La nota está vacía."), 400

    instructions = {
        "summarize": "Resumí el texto en español usando una lista breve de viñetas.",
        "improve": "Mejorá la redacción del texto en español sin cambiar su significado.",
        "continue": "Continuá el texto en español manteniendo el tono y el estilo.",
        "translate": "Traducí el texto al inglés manteniendo el formato Markdown.",
    }

    if action == "custom":
        if not instruction:
            return jsonify(ok=False, error="Escribí una instrucción para la IA."), 400
        task = instruction
    else:
        task = instructions.get(action, instructions["improve"])

    prompt = (
        f"{task}\n\n"
        "Respondé únicamente con el resultado, sin explicaciones ni comentarios. "
        "Usá Markdown cuando corresponda.\n\n"
        f"Texto:\n{source}"
    )

    try:
        text = generate_text(prompt)
    except LlmError as error:
        return jsonify(ok=False, error=str(error)), 502

    if not text:
        return jsonify(ok=False, error="La IA no devolvió texto."), 502

    return jsonify(ok=True, text=text)


@bp.route("/<int:note_id>/tags", methods=["POST"])
@login_required
def update_note_tags(note_id):
    note = note_owner_or_404(note_id)
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
    note = note_owner_or_404(note_id)
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
    note = note_owner_or_404(note_id)
    form = MoveNoteForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return safe_next("notes.list_notes")

    directory_value = form.directory_id.data or ""
    directory = directory_or_none(directory_value)

    if directory_value and not directory:
        flash("Elegí una carpeta válida.", "warning")
        return safe_next("notes.list_notes")

    note.directory_id = directory.id if directory else None
    note.modified_at = utcnow()
    db.session.commit()

    if directory:
        flash(f"Nota movida a «{directory.name}».", "success")
        return safe_next("notes.folders", directory_id=directory.id)

    flash("La nota quedó sin carpeta.", "success")
    return safe_next("notes.list_notes")


@bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = note_owner_or_404(note_id)
    note.to_delete = True
    note.deleted_at = utcnow()
    db.session.commit()

    flash("Nota movida a la papelera.", "success")
    return safe_next("notes.list_notes")


@bp.route("/<int:note_id>/export/<string:export_format>")
@login_required
def export_note(note_id, export_format):
    note, _ = note_for_access(note_id)
    return export_response(note, export_format)


@bp.route("/<int:note_id>/images", methods=["POST"])
@login_required
def upload_note_image(note_id):
    note_for_access(note_id, write=True)
    form = ImageUploadForm()

    if not form.validate_on_submit():
        return jsonify(ok=False, error=form_error(form)), 400

    try:
        image_url = save_image(form.image.data, current_user.id)
    except StorageError as error:
        return jsonify(ok=False, error=str(error)), 400

    alt = (form.alt.data or "Imagen").replace("[", "").replace("]", "").strip()
    alt = alt or "Imagen"

    return jsonify(
        ok=True,
        url=image_url,
        markdown=f"![{alt}]({image_url})",
    )


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_image(filename):
    return send_from_directory(upload_root(), filename)


@bp.route("/<int:note_id>/share/search")
@login_required
def share_search(note_id):
    note = note_owner_or_404(note_id)
    query = (request.args.get("q") or "").strip()
    excluded = {collab.user_id for collab in note.collabs}
    excluded.add(current_user.id)

    users = User.query.filter(~User.id.in_(excluded))

    if query:
        pattern = f"%{query}%"
        users = users.filter(
            or_(User.name.ilike(pattern), User.email.ilike(pattern))
        )

    users = users.order_by(func.lower(User.name)).limit(8).all()

    return jsonify(
        users=[
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatar": user.avatar,
            }
            for user in users
        ]
    )


@bp.route("/<int:note_id>/share", methods=["POST"])
@login_required
def share_note(note_id):
    note = note_owner_or_404(note_id)
    form = ShareNoteForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return safe_next("notes.edit_note", note_id=note.id)

    try:
        user_id = int(form.user_id.data)
    except (TypeError, ValueError):
        flash("Elegí una cuenta válida para compartir.", "warning")
        return safe_next("notes.edit_note", note_id=note.id)

    user = db.session.get(User, user_id)

    if not user or user.id == current_user.id:
        flash("Elegí una cuenta válida para compartir.", "warning")
        return safe_next("notes.edit_note", note_id=note.id)

    collab = Collab.query.filter_by(note_id=note.id, user_id=user.id).first()

    if collab:
        collab.permission = form.permission.data
        message = f"Permiso de {user.name} actualizado."
    else:
        db.session.add(
            Collab(
                permission=form.permission.data,
                user_id=user.id,
                note_id=note.id,
            )
        )
        message = f"Nota compartida con {user.name}."

    db.session.commit()
    flash(message, "success")
    return safe_next("notes.edit_note", note_id=note.id)


@bp.route("/<int:note_id>/share/<int:user_id>/remove", methods=["POST"])
@login_required
def unshare_note(note_id, user_id):
    note = note_owner_or_404(note_id)
    collab = Collab.query.filter_by(note_id=note.id, user_id=user_id).first()

    if not collab:
        abort(404)

    db.session.delete(collab)
    db.session.commit()

    flash("Se quitó el acceso a la nota.", "success")
    return safe_next("notes.edit_note", note_id=note.id)


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
            return redirect(url_for("notes.list_notes"))
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
    form = FolderForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return safe_next("notes.folders")

    parent = directory_or_none(form.parent_id.data)

    directory = Directory(
        name=form.name.data[:NoteLength.NAME],
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
    form = FolderForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
    else:
        directory.name = form.name.data[:NoteLength.NAME]
        db.session.commit()
        flash("Carpeta renombrada.", "success")

    return safe_next("notes.folders", directory_id=directory.id)


@bp.route("/folders/<int:directory_id>/delete", methods=["POST"])
@login_required
def delete_folder(directory_id):
    directory = directory_or_404(directory_id)
    fallback = directory.parent
    folder_name = directory.name

    db.session.delete(directory)
    db.session.commit()

    flash(
        f"Carpeta «{folder_name}» eliminada junto con sus subcarpetas y notas.",
        "success",
    )

    if fallback:
        return redirect(url_for("notes.folders", directory_id=fallback.id))

    return redirect(url_for("notes.list_notes"))


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
    form = TagForm()

    if not form.validate_on_submit():
        flash(form_error(form), "warning")
        return safe_next("notes.tags")

    name = form.name.data.lstrip("#").strip()

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
            directory_id=directory.id if directory else None,
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
