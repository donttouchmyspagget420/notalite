from src.extensions import db
from src.models import Collab, Note
from src.tests.base import BaseTestCase


class SearchTestCase(BaseTestCase):
    def test_search_page_loads(self):
        response = self.client.get("/notes/search")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Buscá en tus notas", response.get_data(as_text=True))

    def test_search_matches_title(self):
        html = self.client.get("/notes/search?q=First").get_data(as_text=True)

        self.assertIn("<mark>First</mark> note", html)

    def test_search_matches_content_with_highlight(self):
        html = self.client.get("/notes/search?q=Hello").get_data(as_text=True)

        self.assertIn("First note", html)
        self.assertIn("<mark>Hello</mark>", html)

    def test_search_matches_tags(self):
        tag = self.create_tag(name="ideas")
        self.note.tags.append(tag)
        db.session.commit()

        html = self.client.get("/notes/search?q=ideas&field=tag").get_data(as_text=True)

        self.assertIn("First note", html)

    def test_title_filter_does_not_search_content(self):
        html = self.client.get("/notes/search?q=Hello&field=title").get_data(as_text=True)

        self.assertIn("No encontramos resultados", html)

    def test_search_includes_shared_notes(self):
        other = self.create_user()
        shared_note = Note(
            title="Shared secret",
            name="shared-secret.md",
            content="A collaborative body",
            user_id=other.id,
        )
        db.session.add(shared_note)
        db.session.commit()
        db.session.add(
            Collab(permission="view", user_id=self.user.id, note_id=shared_note.id)
        )
        db.session.commit()

        html = self.client.get("/notes/search?q=collaborative").get_data(as_text=True)

        self.assertIn("Shared secret", html)

    def test_search_escapes_html(self):
        self.note.title = "<script>alert(1)</script>"
        db.session.commit()

        html = self.client.get("/notes/search?q=script").get_data(as_text=True)

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;", html)
        self.assertIn("&gt;", html)

    def test_thumbnail_filter_uses_first_image(self):
        self.note.content = "![shot](/notes/uploads/picture.png)"
        db.session.commit()

        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertIn('src="/notes/uploads/picture.png"', html)

    def test_home_lists_delete_action(self):
        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertIn(f"/notes/{self.note.id}/delete", html)
