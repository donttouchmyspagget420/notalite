from src.extensions import db
from src.models import Tag
from tests.base import BaseTestCase


class TagsTestCase(BaseTestCase):
    def test_create_tag(self):
        response = self.client.post("/notes/tags/create", data={"name": "ideas"})

        self.assertEqual(response.status_code, 302)
        tag = Tag.query.filter_by(user_id=self.user.id, nombre="ideas").one()
        self.assertIn(f"/notes/tags/{tag.id}", response.headers["Location"])

    def test_duplicate_tag_is_reused(self):
        tag = self.create_tag(name="ideas")

        response = self.client.post("/notes/tags/create", data={"name": "#Ideas"})

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/notes/tags/{tag.id}", response.headers["Location"])
        self.assertEqual(Tag.query.filter_by(user_id=self.user.id).count(), 1)

    def test_assign_and_remove_tag(self):
        tag = self.create_tag(name="ideas")

        self.client.post(
            f"/notes/{self.note.id}/tags",
            data={"tag_ids": [str(tag.id)]},
        )
        db.session.refresh(self.note)
        self.assertEqual([item.id for item in self.note.tags], [tag.id])

        self.client.post(f"/notes/{self.note.id}/tags/{tag.id}/remove")
        db.session.refresh(self.note)
        self.assertEqual(self.note.tags, [])

    def test_delete_tag_removes_it_from_notes(self):
        tag = self.create_tag(name="ideas")
        self.note.tags.append(tag)
        db.session.commit()

        response = self.client.post(f"/notes/tags/{tag.id}/delete")

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(Tag, tag.id))
        db.session.refresh(self.note)
        self.assertEqual(self.note.tags, [])

    def test_tag_page_renders_unfiled_notes(self):
        tag = self.create_tag(name="ideas")
        self.note.directory_id = None
        self.note.tags.append(tag)
        db.session.commit()

        html = self.client.get(f"/notes/tags/{tag.id}").get_data(as_text=True)

        self.assertEqual(self.client.get(f"/notes/tags/{tag.id}").status_code, 200)
        self.assertIn("Sin carpeta", html)
