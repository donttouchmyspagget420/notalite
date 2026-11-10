from datetime import timedelta

from src.extensions import db
from src.models import Note, utcnow
from src.tests.base import BaseTestCase


class TrashTestCase(BaseTestCase):
    def test_delete_moves_note_to_trash(self):
        self.client.post(f"/notes/{self.note.id}/delete")

        note = db.session.get(Note, self.note.id)
        self.assertTrue(note.to_delete)
        self.assertIsNotNone(note.deleted_at)

        html = self.client.get("/notes/trash").get_data(as_text=True)
        self.assertIn("First note", html)

    def test_trash_is_hidden_from_home(self):
        self.client.post(f"/notes/{self.note.id}/delete")

        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertNotIn("First note", html)

    def test_restore_note(self):
        self.client.post(f"/notes/{self.note.id}/delete")

        response = self.client.post(f"/notes/{self.note.id}/restore")

        self.assertEqual(response.status_code, 302)
        note = db.session.get(Note, self.note.id)
        self.assertFalse(note.to_delete)
        self.assertIsNone(note.deleted_at)

    def test_destroy_note_permanently(self):
        self.client.post(f"/notes/{self.note.id}/delete")

        response = self.client.post(f"/notes/{self.note.id}/destroy")

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(Note, self.note.id))

    def test_empty_trash(self):
        self.client.post(f"/notes/{self.note.id}/delete")

        response = self.client.post("/notes/trash/empty")

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(Note, self.note.id))

    def test_expired_notes_are_purged(self):
        self.note.to_delete = True
        self.note.deleted_at = utcnow() - timedelta(days=31)
        db.session.commit()

        self.client.get("/notes/trash")

        self.assertIsNone(db.session.get(Note, self.note.id))

    def test_cannot_restore_another_users_note(self):
        other = self.create_user()
        other_note = Note(
            title="Private",
            name="private.md",
            content="secret",
            to_delete=True,
            deleted_at=utcnow(),
            user_id=other.id,
        )
        db.session.add(other_note)
        db.session.commit()

        response = self.client.post(f"/notes/{other_note.id}/restore")

        self.assertEqual(response.status_code, 404)
