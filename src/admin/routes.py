import os
from datetime import datetime, timedelta
from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
    or_,
    select,
)
from sqlalchemy.exc import SQLAlchemyError

from src.admin import bp
from src.extensions import bcrypt, db
from src.models import (
    Collab,
    Directory,
    Note,
    Pending,
    Role,
    Tag,
    User,
    note_tags,
    utcnow,
)
from src.notes.utils import sidebar_data
from src.services.storage import StorageError, save_image, upload_root

PAGE_SIZE = 25
ROW_SEPARATOR = "|"
MISSING = object()

TABLE_LABELS = {
    "users": "Usuarios",
    "roles": "Roles",
    "pendings": "Registros pendientes",
    "directories": "Carpetas",
    "notes": "Notas",
    "tags": "Etiquetas",
    "collabs": "Colaboraciones",
    "note_tags": "Notas y etiquetas",
}

COLUMN_LABELS = {
    "id": "ID",
    "g_id": "Google ID",
    "name": "Nombre",
    "title": "Título",
    "content": "Contenido",
    "email": "Email",
    "password": "Contraseña",
    "avatar": "Avatar",
    "timestamp": "Alta",
    "role_id": "Rol",
    "parent_id": "Carpeta padre",
    "user_id": "Usuario",
    "directory_id": "Carpeta",
    "note_id": "Nota",
    "tag_id": "Etiqueta",
    "created_at": "Creada",
    "modified_at": "Modificada",
    "deleted_at": "Eliminada",
    "to_delete": "En papelera",
    "permission": "Permiso",
    "nombre": "Nombre",
    "color": "Color",
    "code": "Código",
    "expires_at": "Expira",
}

MODELS_BY_TABLE = {
    "roles": Role,
    "users": User,
    "pendings": Pending,
    "directories": Directory,
    "notes": Note,
    "tags": Tag,
    "collabs": Collab,
}


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


def managed_tables():
    return sorted(
        db.metadata.tables.values(),
        key=lambda table: (
            list(TABLE_LABELS).index(table.name)
            if table.name in TABLE_LABELS
            else len(TABLE_LABELS),
            table.name,
        ),
    )


def table_or_404(table_name):
    table = db.metadata.tables.get(table_name)

    if table is None:
        abort(404)

    return table


def table_label(table):
    return TABLE_LABELS.get(table.name, table.name)


def column_label(column):
    return COLUMN_LABELS.get(
        column.name, column.name.replace("_", " ").capitalize()
    )


def primary_key_columns(table):
    return list(table.primary_key.columns)


def is_auto_primary_key(table, column):
    return (
        column.primary_key
        and len(primary_key_columns(table)) == 1
        and isinstance(column.type, Integer)
    )


def has_editable_columns(table):
    return any(not column.primary_key for column in table.columns)


def row_key_for(table, row):
    return ROW_SEPARATOR.join(
        str(row[column.name]) for column in primary_key_columns(table)
    )


def coerce_primary_key(column, value):
    if isinstance(column.type, Integer):
        try:
            return int(value)
        except (TypeError, ValueError):
            abort(404)

    return value


def row_filters(table, row_key):
    columns = primary_key_columns(table)
    parts = row_key.split(ROW_SEPARATOR) if len(columns) > 1 else [row_key]

    if len(parts) != len(columns):
        abort(404)

    return [
        column == coerce_primary_key(column, value)
        for column, value in zip(columns, parts)
    ]


def get_row(table, row_key):
    row = db.session.execute(
        select(table).where(*row_filters(table, row_key))
    ).mappings().first()

    if row is None:
        abort(404)

    return row


def row_count(table):
    return db.session.scalar(select(func.count()).select_from(table)) or 0


def display_value(column, value):
    if value is None:
        return "—"

    if column.name == "password":
        return "••••••"

    if isinstance(column.type, Boolean):
        return "Sí" if value else "No"

    if isinstance(column.type, DateTime):
        return value.strftime("%Y-%m-%d %H:%M")

    text = str(value)
    return text if len(text) <= 70 else f"{text[:67]}…"


def form_display_value(column, value):
    if value is None:
        return ""

    if isinstance(column.type, DateTime):
        return value.strftime("%Y-%m-%dT%H:%M")

    return str(value)


def hash_password_if_needed(value):
    if value and not value.startswith(("$2a$", "$2b$", "$2y$", "$2x$")):
        return bcrypt.generate_password_hash(value).decode("utf-8")

    return value


def parse_column_value(column, raw, creating):
    if isinstance(column.type, Boolean):
        return raw is not None

    raw = (raw or "").strip()

    if raw == "":
        if creating and (
            column.default is not None or column.server_default is not None
        ):
            return MISSING

        if column.nullable:
            return None

        if isinstance(column.type, Text):
            return ""

        raise ValueError(f"«{column_label(column)}» es obligatorio.")

    if isinstance(column.type, Integer):
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise ValueError(
                f"«{column_label(column)}» debe ser un número entero."
            ) from None

    if isinstance(column.type, DateTime):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            raise ValueError(
                f"«{column_label(column)}» no es una fecha válida."
            ) from None

    if isinstance(column.type, Enum):
        allowed = column.type.enums

        if raw not in allowed:
            raise ValueError(
                f"«{column_label(column)}» debe ser uno de: "
                f"{', '.join(allowed)}."
            )

        return raw

    return raw


def parse_table_form(table, row=None):
    creating = row is None
    values = {}
    errors = []

    for column in table.columns:
        if not creating and column.primary_key:
            continue

        if creating and is_auto_primary_key(table, column):
            continue

        if table.name == "users" and column.name == "avatar":
            upload = request.files.get(column.name)

            if upload and upload.filename:
                target_id = row["id"] if row is not None else current_user.id

                try:
                    values[column.name] = save_image(upload, target_id)
                except StorageError as error:
                    errors.append(str(error))

            continue

        raw = request.form.get(column.name)

        if (
            table.name == "users"
            and column.name == "password"
            and not creating
            and not (raw or "").strip()
        ):
            continue

        try:
            value = parse_column_value(column, raw, creating)
        except ValueError as error:
            errors.append(str(error))
            continue

        if value is MISSING:
            continue

        if table.name == "users" and column.name == "password":
            value = hash_password_if_needed(value)

        values[column.name] = value

    if (
        table.name == "users"
        and row is not None
        and row["id"] == current_user.id
        and "role_id" in values
    ):
        role = db.session.get(Role, values["role_id"])

        if not role or (role.name or "").strip().lower() != "admin":
            errors.append(
                "No podés quitarte el rol de administrador a vos mismo."
            )

    return values, errors


def relation_options(column):
    foreign_key = next(iter(column.foreign_keys), None)

    if foreign_key is None:
        return []

    referenced = foreign_key.column.table
    keys = primary_key_columns(referenced)
    label_name = next(
        (
            name
            for name in ("name", "title", "nombre", "email")
            if name in referenced.c
        ),
        keys[0].name,
    )
    rows = db.session.execute(
        select(referenced).order_by(referenced.c[label_name])
    ).mappings().all()
    options = []

    for row in rows:
        key = (
            row[keys[0].name]
            if len(keys) == 1
            else ROW_SEPARATOR.join(str(row[item.name]) for item in keys)
        )
        label = str(row[label_name] or "")

        if referenced.name == "users" and "email" in referenced.c:
            label = f"{row['name']} · {row['email']}"

        label = label[:70] or str(key)
        options.append(
            {
                "value": str(key),
                "label": f"{label} ({key})",
            }
        )

    return options


def build_form_fields(table, row, values, form_data=None):
    fields = []

    for column in table.columns:
        if row is None and is_auto_primary_key(table, column):
            continue

        readonly = row is not None and column.primary_key

        if table.name == "users" and column.name == "avatar":
            raw_value = (
                row[column.name] if row is not None else values.get(column.name)
            )
        elif readonly:
            raw_value = row[column.name]
        elif form_data is not None and column.name in form_data:
            raw_value = form_data.get(column.name)
        elif row is not None:
            raw_value = row[column.name]
        else:
            raw_value = values.get(column.name)

        if (
            table.name == "users"
            and column.name == "password"
            and row is not None
            and form_data is None
        ):
            raw_value = ""

        field = {
            "name": column.name,
            "label": column_label(column),
            "nullable": column.nullable,
            "readonly": readonly,
            "help": "",
            "value": form_display_value(column, raw_value),
            "checked": bool(raw_value),
            "options": [],
            "type": "text",
        }

        foreign_keys = list(column.foreign_keys)

        if table.name == "users" and column.name == "avatar":
            field["type"] = "file"
            field["value"] = "" if raw_value is None else str(raw_value)
        elif isinstance(column.type, Boolean):
            field["type"] = "checkbox"
        elif isinstance(column.type, DateTime):
            field["type"] = "datetime-local"
        elif foreign_keys:
            field["type"] = "select"
            field["options"] = relation_options(column)
            field["value"] = "" if raw_value is None else str(raw_value)
        elif isinstance(column.type, Enum):
            field["type"] = "select"
            field["options"] = [
                {"value": value, "label": value}
                for value in column.type.enums
            ]
            field["value"] = "" if raw_value is None else str(raw_value)
        elif isinstance(column.type, Text):
            field["type"] = "textarea"
        elif isinstance(column.type, Integer):
            field["type"] = "number"

        if table.name == "users" and column.name == "avatar":
            field["help"] = (
                "Subí una imagen (PNG, JPG, GIF o WebP). "
                + (
                    "Si no elegís un archivo, se conserva el avatar actual."
                    if row is not None
                    else "Opcional."
                )
            )
        elif column.name == "password":
            field["help"] = (
                "Escribí texto plano para hashearlo, o pegá un hash bcrypt. "
                + (
                    "Dejalo en blanco para conservar la contraseña actual."
                    if row is not None
                    else "Podés dejarlo en blanco para cuentas de Google."
                )
            )
        elif foreign_keys:
            field["help"] = "Seleccioná un registro existente."
        elif column.nullable and not readonly:
            field["help"] = "Opcional."

        fields.append(field)

    return fields


def render_table_form(table, row, values, errors):
    form_data = request.form if request.method == "POST" else None

    return render_template(
        "admin/table_form.html",
        table=table,
        table_label=table_label(table),
        row=row,
        row_key=row_key_for(table, row) if row is not None else None,
        fields=build_form_fields(table, row, values, form_data),
        errors=errors,
        creating=row is None,
        **sidebar_data(),
    )


@bp.route("/")
@login_required
@admin_required
def dashboard():
    all_notes = Note.query.all()
    active_notes = [note for note in all_notes if not note.to_delete]
    trashed_notes = len(all_notes) - len(active_notes)
    total_users = User.query.count()
    cutoff = utcnow() - timedelta(days=30)
    active_user_ids = {
        note.user_id
        for note in active_notes
        if note.modified_at and as_utc(note.modified_at, cutoff) >= cutoff
    }
    total_directories = Directory.query.count()
    root_directories = Directory.query.filter_by(parent_id=None).count()
    total_tags = Tag.query.count()
    tag_assignments = (
        db.session.scalar(select(func.count()).select_from(note_tags)) or 0
    )
    total_collabs = Collab.query.count()
    pending_count = Pending.query.count()

    stats = [
        {
            "label": "Usuarios totales",
            "value": total_users,
            "detail": f"{len(active_user_ids)} activos en 30 días",
        },
        {
            "label": "Notas activas",
            "value": len(active_notes),
            "detail": f"{trashed_notes} en papelera",
        },
        {
            "label": "Carpetas",
            "value": total_directories,
            "detail": (
                f"{root_directories} raíz · "
                f"{total_directories - root_directories} subcarpetas"
            ),
        },
        {
            "label": "Etiquetas",
            "value": total_tags,
            "detail": f"{tag_assignments} asignaciones",
        },
        {
            "label": "Colaboraciones",
            "value": total_collabs,
            "detail": f"{pending_count} invitaciones pendientes",
        },
        {
            "label": "Almacenamiento",
            "value": human_size(directory_size(upload_root())),
            "detail": "imágenes y adjuntos",
        },
    ]

    role_rows = db.session.execute(
        select(Role.name, func.count(User.id).label("total"))
        .outerjoin(User, User.role_id == Role.id)
        .group_by(Role.id, Role.name)
        .order_by(func.count(User.id).desc(), Role.name)
    ).all()
    role_maximum = max((row.total for row in role_rows), default=0) or 1
    role_distribution = [
        {
            "label": row.name,
            "count": row.total,
            "width": round(row.total / role_maximum * 100),
        }
        for row in role_rows
    ]

    top_tag_rows = db.session.execute(
        select(
            Tag.nombre,
            func.count(note_tags.c.note_id).label("total"),
        )
        .join(note_tags, note_tags.c.tag_id == Tag.id)
        .group_by(Tag.id, Tag.nombre)
        .order_by(func.count(note_tags.c.note_id).desc(), Tag.nombre)
        .limit(10)
    ).all()
    tag_maximum = max((row.total for row in top_tag_rows), default=0) or 1
    top_tags = [
        {
            "label": row.nombre,
            "count": row.total,
            "width": round(row.total / tag_maximum * 100),
        }
        for row in top_tag_rows
    ]

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        activity=weekly_activity(all_notes),
        role_distribution=role_distribution,
        top_tags=top_tags,
        **sidebar_data(),
    )


@bp.route("/tables")
@login_required
@admin_required
def tables():
    tables_list = [
        {
            "name": table.name,
            "label": table_label(table),
            "rows": row_count(table),
            "columns": len(table.columns),
        }
        for table in managed_tables()
    ]

    return render_template(
        "admin/tables.html",
        tables=tables_list,
        **sidebar_data(),
    )


@bp.route("/tables/<string:table_name>")
@login_required
@admin_required
def table_rows(table_name):
    table = table_or_404(table_name)
    query = (request.args.get("q") or "").strip()
    page = max(1, request.args.get("page", 1, type=int) or 1)
    statement = select(table)

    if query:
        string_columns = [
            column
            for column in table.columns
            if isinstance(column.type, (String, Text))
        ]

        if string_columns:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(*[column.ilike(pattern) for column in string_columns])
            )

    total = (
        db.session.scalar(select(func.count()).select_from(statement.subquery()))
        or 0
    )
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    keys = primary_key_columns(table)
    rows = db.session.execute(
        statement.order_by(*keys)
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).mappings().all()

    return render_template(
        "admin/table_rows.html",
        table=table,
        table_label=table_label(table),
        columns=[
            {"name": column.name, "label": column_label(column)}
            for column in table.columns
        ],
        rows=[
            {
                "key": row_key_for(table, row),
                "cells": [
                    {
                        "name": column.name,
                        "value": display_value(column, row[column.name]),
                        "avatar": (
                            table.name == "users"
                            and column.name == "avatar"
                        ),
                        "raw": row[column.name],
                    }
                    for column in table.columns
                ],
            }
            for row in rows
        ],
        total=total,
        page=page,
        pages=pages,
        query=query,
        can_edit=has_editable_columns(table),
        **sidebar_data(),
    )


@bp.route("/tables/<string:table_name>/new", methods=["GET", "POST"])
@login_required
@admin_required
def table_row_new(table_name):
    table = table_or_404(table_name)
    values = {}
    errors = []

    if request.method == "POST":
        values, errors = parse_table_form(table)

        if not errors:
            try:
                db.session.execute(table.insert().values(**values))
                db.session.commit()
                flash("Fila creada.", "success")
                return redirect(
                    url_for("admin.table_rows", table_name=table.name)
                )
            except SQLAlchemyError as error:
                db.session.rollback()
                errors.append(f"No se pudo crear la fila: {error.orig}")

    return render_table_form(table, None, values, errors)


@bp.route("/tables/<string:table_name>/<path:row_key>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def table_row_edit(table_name, row_key):
    table = table_or_404(table_name)
    row = get_row(table, row_key)
    values = {}
    errors = []

    if request.method == "POST":
        values, errors = parse_table_form(table, row)

        if not errors and not values:
            flash("Esta tabla no tiene columnas editables.", "warning")
            return redirect(
                url_for("admin.table_rows", table_name=table.name)
            )

        if not errors:
            try:
                db.session.execute(
                    table.update()
                    .where(*row_filters(table, row_key))
                    .values(**values)
                )
                db.session.commit()
                flash("Fila actualizada.", "success")
                return redirect(
                    url_for("admin.table_rows", table_name=table.name)
                )
            except SQLAlchemyError as error:
                db.session.rollback()
                errors.append(f"No se pudo actualizar la fila: {error.orig}")

    return render_table_form(table, row, values, errors)


@bp.route("/tables/<string:table_name>/<path:row_key>/delete", methods=["POST"])
@login_required
@admin_required
def table_row_delete(table_name, row_key):
    table = table_or_404(table_name)
    row = get_row(table, row_key)

    if table.name == "users" and row["id"] == current_user.id:
        flash("No podés eliminar tu propia cuenta.", "warning")
        return redirect(url_for("admin.table_rows", table_name=table.name))

    model = MODELS_BY_TABLE.get(table.name)

    try:
        if model is not None:
            keys = primary_key_columns(table)

            if len(keys) == 1:
                instance = db.session.get(
                    model, coerce_primary_key(keys[0], row[keys[0].name])
                )
            else:
                instance = db.session.get(
                    model,
                    tuple(
                        coerce_primary_key(column, row[column.name])
                        for column in keys
                    ),
                )

            if instance is None:
                abort(404)

            db.session.delete(instance)
        else:
            db.session.execute(
                table.delete().where(*row_filters(table, row_key))
            )

        db.session.commit()
        flash("Fila eliminada.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash(
            "No se pudo eliminar la fila. Puede tener registros relacionados.",
            "warning",
        )

    return redirect(url_for("admin.table_rows", table_name=table.name))
