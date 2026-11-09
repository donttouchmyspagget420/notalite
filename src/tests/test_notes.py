import io

from src.extensions import db
from src.models import Directory, Note
from src.tests.base import BaseTestCase


class NotesTestCase(BaseTestCase):
    def test_can_create_note_without_folder(self):
        response = self.client.post(
            "/notes/create",
            data={"title": "Unfiled note", "mode": "blank"},
        )

        self.assertEqual(response.status_code, 302)
        note = Note.query.filter_by(user_id=self.user.id, title="Unfiled note").one()
        self.assertIsNone(note.directory_id)

    def test_note_list_marks_unfiled_notes(self):
        self.note.directory_id = None
        db.session.commit()

        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertIn("Sin carpeta", html)

    def test_delete_last_folder_deletes_its_notes(self):
        response = self.client.post(f"/notes/folders/{self.folder.id}/delete")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Directory.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertIsNone(db.session.get(Note, self.note.id))

    def test_folders_redirects_to_list_without_folders(self):
        self.client.post(f"/notes/folders/{self.folder.id}/delete")

        response = self.client.get("/notes/folders")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/notes/list"))

    def test_sidebar_reports_missing_folders(self):
        self.client.post(f"/notes/folders/{self.folder.id}/delete")

        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertIn("Todavía no hay carpetas", html)

    def test_folder_page_uses_note_and_folder_icons(self):
        subfolder = Directory(name="Child", user_id=self.user.id, parent_id=self.folder.id)
        db.session.add(subfolder)
        db.session.commit()

        html = self.client.get(f"/notes/folders/{self.folder.id}").get_data(as_text=True)

        self.assertIn("note-row-file", html)
        self.assertIn("note-row-folder", html)

    def test_tree_page_renders(self):
        response = self.client.get("/notes/folders/tree")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Vista jerárquica", response.get_data(as_text=True))

    def test_move_note_to_no_folder(self):
        response = self.client.post(
            f"/notes/{self.note.id}/move",
            data={"directory_id": "", "next": "/notes/list"},
        )

        self.assertEqual(response.status_code, 302)
        note = db.session.get(Note, self.note.id)
        self.assertIsNone(note.directory_id)

    def test_move_note_rejects_unknown_folder(self):
        response = self.client.post(
            f"/notes/{self.note.id}/move",
            data={"directory_id": "999999", "next": "/notes/list"},
        )

        self.assertEqual(response.status_code, 302)
        note = db.session.get(Note, self.note.id)
        self.assertEqual(note.directory_id, self.folder.id)

    def test_delete_folder_deletes_children_and_notes(self):
        child = Directory(name="Child", user_id=self.user.id, parent_id=self.folder.id)
        db.session.add(child)
        db.session.commit()

        child_note = Note(
            title="Child note",
            name="child-note.md",
            content="Child",
            user_id=self.user.id,
            directory_id=child.id,
        )
        db.session.add(child_note)
        db.session.commit()

        child_id = child.id
        child_note_id = child_note.id

        self.client.post(f"/notes/folders/{self.folder.id}/delete")

        self.assertIsNone(db.session.get(Directory, child_id))
        self.assertIsNone(db.session.get(Note, self.note.id))
        self.assertIsNone(db.session.get(Note, child_note_id))

    def test_import_without_folder(self):
        response = self.client.post(
            "/notes/import",
            data={
                "directory_id": "",
                "files": (io.BytesIO(b"# Imported\n\nBody"), "imported.md"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 302)
        note = Note.query.filter_by(user_id=self.user.id, name="imported.md").one()
        self.assertIsNone(note.directory_id)
        self.assertEqual(note.title, "Imported")

    def test_export_markdown(self):
        response = self.client.get(f"/notes/{self.note.id}/export/md")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response.headers["Content-Type"])
        self.assertIn(b"# First note", response.data)

    def test_export_pdf(self):
        response = self.client.get(f"/notes/{self.note.id}/export/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_cannot_open_another_users_note(self):
        other = self.create_user()
        other_note = Note(
            title="Private",
            name="private.md",
            content="secret",
            user_id=other.id,
        )
        db.session.add(other_note)
        db.session.commit()

        response = self.client.get(f"/notes/{other_note.id}")

        self.assertEqual(response.status_code, 404)
