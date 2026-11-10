from src.extensions import bcrypt, db
from src.models import Role, User
from src.tests.base import BaseTestCase


class AdminTestCase(BaseTestCase):
    def create_role_user(self, role_name):
        role = Role.query.filter_by(name=role_name).first()

        if not role:
            role = Role(name=role_name)
            db.session.add(role)
            db.session.commit()

        user = User(
            name=f"{role_name} User",
            email=f"{role_name.lower()}@example.com",
            password=bcrypt.generate_password_hash("Password123!").decode("utf-8"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_dashboard_loads_for_admin(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Usuarios y métricas", html)
        self.assertIn("Notas activas", html)
        self.assertIn("admin.css", html)

    def test_dashboard_requires_login(self):
        response = self.app.test_client().get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_dashboard_rejects_non_admin(self):
        user = self.create_role_user("Viewer")
        self.login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 403)

    def test_user_search_filters_results(self):
        self.create_role_user("Editor")

        html = self.client.get("/admin/?q=editor").get_data(as_text=True)

        self.assertIn("Usuarios que coinciden con «editor»", html)
        self.assertIn("editor@example.com", html)
