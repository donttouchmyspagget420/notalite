from src.extensions import bcrypt, db
from src.models import User
from src.tests.base import BaseTestCase


class SettingsTestCase(BaseTestCase):
    def test_settings_page_renders(self):
        response = self.client.get("/settings/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Perfil", html)
        self.assertIn("Cambiar contraseña", html)
        self.assertIn("Apariencia", html)

    def test_settings_requires_login(self):
        response = self.app.test_client().get("/settings/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_update_profile(self):
        response = self.client.post(
            "/settings/profile",
            data={
                "name": "Updated Name",
                "email": "updated@example.com",
                "avatar": "https://example.com/avatar.png",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = db.session.get(User, self.user.id)
        self.assertEqual(user.name, "Updated Name")
        self.assertEqual(user.email, "updated@example.com")
        self.assertEqual(user.avatar, "https://example.com/avatar.png")

    def test_profile_rejects_duplicate_email(self):
        other = self.create_user(email="taken@example.com")
        other_email = other.email

        self.client.post(
            "/settings/profile",
            data={"name": "Test User", "email": other.email, "avatar": ""},
        )

        user = db.session.get(User, self.user.id)
        self.assertEqual(user.email, "test@example.com")

    def test_profile_requires_name_and_email(self):
        self.client.post(
            "/settings/profile",
            data={"name": "", "email": "", "avatar": ""},
        )

        user = db.session.get(User, self.user.id)
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@example.com")

    def test_change_password(self):
        response = self.client.post(
            "/settings/password",
            data={
                "current_password": "Password123!",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = db.session.get(User, self.user.id)
        self.assertTrue(bcrypt.check_password_hash(user.password, "NewPassword123!"))

    def test_password_rejects_wrong_current_password(self):
        self.client.post(
            "/settings/password",
            data={
                "current_password": "wrong",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )

        user = db.session.get(User, self.user.id)
        self.assertTrue(bcrypt.check_password_hash(user.password, "Password123!"))

    def test_password_rejects_mismatch(self):
        self.client.post(
            "/settings/password",
            data={
                "current_password": "Password123!",
                "new_password": "NewPassword123!",
                "confirm_password": "Different123!",
            },
        )

        user = db.session.get(User, self.user.id)
        self.assertTrue(bcrypt.check_password_hash(user.password, "Password123!"))

    def test_theme_switch(self):
        response = self.client.post("/settings/theme", data={"theme": "light"})

        self.assertEqual(response.status_code, 302)
        html = self.client.get("/settings/").get_data(as_text=True)
        self.assertIn('data-bs-theme="light"', html)

    def test_invalid_theme_falls_back_to_dark(self):
        self.client.post("/settings/theme", data={"theme": "neon"})

        html = self.client.get("/settings/").get_data(as_text=True)
        self.assertIn('data-bs-theme="dark"', html)
