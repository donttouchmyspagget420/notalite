from datetime import datetime, timedelta, timezone

from flask_login import UserMixin

from src.extensions import db


def utcnow():
    return datetime.now(timezone.utc)

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)

    users = db.relationship("User", back_populates="role")
    pendings = db.relationship(
        "Pending", back_populates="role", cascade="all, delete-orphan"
    )

class User(db.Model,UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    # google id 
    g_id = db.Column(db.String(100), unique = True, nullable = True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(255), unique = True, nullable = False)
    # nullable por gente que usa google id
    password = db.Column(db.String(255), nullable = True)
    avatar = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime(timezone = True), default = utcnow)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable = False,
    )

    role = db.relationship("Role", back_populates = "users")
    directories = db.relationship(
        "Directory", back_populates="user", cascade="all, delete-orphan"
    )
    notes = db.relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )
    collabs = db.relationship(
        "Collab", back_populates="user", cascade="all, delete-orphan"
    )
    tags = db.relationship(
        "Tag", back_populates="user", cascade="all, delete-orphan"
    )

class Pending(db.Model):
    __tablename__ = 'pendings'

    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(255), primary_key = True)
    password = db.Column(db.String(255), nullable = False)
    code = db.Column(db.String(255), nullable = False)
    expires_at = db.Column(db.DateTime(timezone = True), default = lambda: utcnow() + timedelta(hours=24))
    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id", ondelete="CASCADE"),
        nullable = False,
    )

    role = db.relationship("Role", back_populates = "pendings")


class Directory(db.Model):
    __tablename__ = 'directories'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable = False,
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("directories.id", ondelete="CASCADE"),
    ) #null significa que es root

    user = db.relationship("User", back_populates="directories")
    parent = db.relationship("Directory", remote_side=[id], back_populates="children")
    children = db.relationship(
        "Directory", back_populates="parent", cascade="all, delete"
    )

    notes = db.relationship(
        "Note", back_populates="directory", cascade="all, delete"
    )

note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(255), nullable = False)
    name = db.Column(db.String(100), nullable = False)
    content = db.Column(db.Text, nullable = False)
    created_at = db.Column(db.DateTime(timezone = True), default = utcnow)
    modified_at = db.Column(db.DateTime(timezone = True), default = utcnow)
    deleted_at = db.Column(db.DateTime(timezone = True))
    to_delete = db.Column(db.Boolean, default = False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable = False,
    )
    directory_id = db.Column(
        db.Integer,
        db.ForeignKey("directories.id", ondelete="CASCADE"),
        nullable = True,
    )

    user = db.relationship("User", back_populates = "notes")
    directory = db.relationship("Directory", back_populates = "notes")
    collabs = db.relationship(
        "Collab", back_populates="note", cascade="all, delete-orphan"
    )
    tags = db.relationship("Tag", secondary=note_tags, back_populates="notes", lazy="select")

class Collab(db.Model):
    __tablename__ = 'collabs'

    id = db.Column(db.Integer, primary_key = True)
    permission = db.Column(db.Enum("view","edit"), nullable = False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable = False,
    )
    note_id = db.Column(
        db.Integer,
        db.ForeignKey("notes.id", ondelete="CASCADE"),
        nullable = False,
    )

    user = db.relationship("User", back_populates = "collabs")
    note = db.relationship("Note", back_populates = "collabs")

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key = True)
    nombre = db.Column(db.String(100), nullable = False)
    color = db.Column(db.String(7), nullable = False, default="#6d6df6") #color en hex como: #ffffff
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable = False,
    )

    user = db.relationship("User", back_populates="tags")
    notes = db.relationship("Note", secondary=note_tags, back_populates="tags", lazy="select")


