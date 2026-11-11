import os
import shutil
import tempfile
import unittest

from config import Config
from src import create_app
from src.extensions import bcrypt, db
from src.models import Directory, Note, Role, Tag, User, utcnow


class BaseTestCase(unittest.TestCase):
    """Creates an isolated database and a logged-in client for each test."""

    def setUp(self):
        file_descriptor, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        self.upload_path = tempfile.mkdtemp()

        class TestConfig(Config):
            TESTING = True
            SECRET_KEY = "test-secret"
            WTF_CSRF_ENABLED = False
            SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.db_path
            UPLOAD_FOLDER = self.upload_path
            GOOGLE_LLM_API_KEY = "test-key"
            GOOGLE_LLM_MODEL = "gemini-test"

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        role = Role(name="Admin")
        db.session.add(role)
        db.session.commit()

        self.user = User(
            name="Test User",
            email="test@example.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
            role_id=role.id,
        )
        db.session.add(self.user)
        db.session.commit()

        self.folder = Directory(name="Root", user_id=self.user.id)
        db.session.add(self.folder)
        db.session.commit()

        self.note = Note(
            title="First note",
            name="first-note.md",
            content="# First note\n\nHello world.",
            created_at=utcnow(),
            modified_at=utcnow(),
            to_delete=False,
            user_id=self.user.id,
            directory_id=self.folder.id,
        )
        db.session.add(self.note)
        db.session.commit()

        self.client = self.app.test_client()
        self.login(self.user)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        os.unlink(self.db_path)
        shutil.rmtree(self.upload_path, ignore_errors=True)

    def login(self, user, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True

    def create_user(self, email="other@example.com", name="Other User"):
        user = User(
            name=name,
            email=email,
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
            role_id=self.user.role_id,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def create_tag(self, name="demo", color="#6d6df6"):
        tag = Tag(nombre=name, color=color, user_id=self.user.id)
        db.session.add(tag)
        db.session.commit()
        return tag
