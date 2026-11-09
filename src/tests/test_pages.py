from src.tests.base import BaseTestCase


class PageSmokeTestCase(BaseTestCase):
    def test_landing_page(self):
        response = self.app.test_client().get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("landing.css", html)
        self.assertIn("NotaLite", html)

    def test_login_and_signup_pages(self):
        client = self.app.test_client()

        for path in ("/auth/login", "/auth/signup"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("landing.css", response.get_data(as_text=True))

    def test_import_export_page_loads_settings_css(self):
        response = self.client.get("/notes/import-export")

        self.assertEqual(response.status_code, 200)
        self.assertIn("settings.css", response.get_data(as_text=True))

    def test_settings_page_loads_settings_css(self):
        response = self.client.get("/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("settings.css", response.get_data(as_text=True))

    def test_app_pages_do_not_load_settings_css(self):
        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertNotIn("settings.css", html)

    def test_editor_page_loads_editor_css(self):
        html = self.client.get(f"/notes/{self.note.id}").get_data(as_text=True)

        self.assertIn("editor.css", html)

    def test_folder_pages_load_folders_css(self):
        folder_html = self.client.get(f"/notes/folders/{self.folder.id}").get_data(as_text=True)
        tree_html = self.client.get("/notes/folders/tree").get_data(as_text=True)

        self.assertIn("folders.css", folder_html)
        self.assertIn("folders.css", tree_html)
