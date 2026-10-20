from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime,timezone

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)

    users = db.relationship("User", back_populates="role")

class User(db.Model,UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(255), unique = True, nullable = False)
    password = db.Column(db.String(255), nullable = False)
    avatar = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime(timezone = True), default = utcnow)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable = False)

    role = db.relationship("Role", back_populates = "users")
    directories = db.relationship("Directory", back_populates="user") 
    notes = db.relationship("Note", back_populates="user")  
    collabs = db.relationship("Collab", back_populates="user") 

class Directory(db.Model):
    __tablename__ = 'directories'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    parent_id = db.Column(db.Integer, db.ForeignKey("directories.id")) #null significa que es root

    user = db.relationship("User", back_populates="directories")
    parent = db.relationship("Directory", remote_side=[id], back_populates="children")
    children = db.relationship("Directory", back_populates="parent")
    
    notes = db.relationship("Note", back_populates="directory")  # Added missing relationship

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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    directory_id = db.Column(db.Integer, db.ForeignKey("directories.id"), nullable = False)

    user = db.relationship("User", back_populates = "notes")
    directory = db.relationship("Directory", back_populates = "notes")
    collabs = db.relationship("Collab", back_populates="note")

class Collab(db.Model):
    __tablename__ = 'collabs'

    id = db.Column(db.Integer, primary_key = True)
    permission = db.Column(db.Enum("view","edit"), nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id"), nullable = False)

    user = db.relationship("User", back_populates = "collabs")
    note = db.relationship("Note", back_populates = "collabs")

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key = True)
    nombre = db.Column(db.String(100), nullable = False)
    color = db.Column(db.String(7), nullable = False) #color en hex como: #ffffff


