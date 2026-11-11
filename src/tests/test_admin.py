import io
import os

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
        self.assertIn("Métricas", html)
        self.assertIn("Notas activas", html)
        self.assertIn("Usuarios por rol", html)
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

    def test_users_table_filters_results(self):
        self.create_role_user("Editor")

        html = self.client.get("/admin/tables/users?q=editor").get_data(
            as_text=True
        )

        self.assertIn("editor@example.com", html)
        self.assertIn("Editor", html)

    def test_admin_views_are_in_sidebar_for_admins(self):
        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertIn("Administración", html)
        self.assertIn('href="/admin/"', html)
        self.assertIn('href="/admin/tables"', html)
        self.assertNotIn('href="/admin/users"', html)

    def test_admin_views_are_hidden_from_non_admins(self):
        viewer = self.create_role_user("Viewer")
        self.login(viewer)

        html = self.client.get("/notes/list").get_data(as_text=True)

        self.assertNotIn('href="/admin/"', html)
        self.assertNotIn('href="/admin/tables"', html)

    def test_removed_users_view_is_gone(self):
        self.assertEqual(self.client.get("/admin/users").status_code, 404)

    def test_admin_can_delete_user(self):
        user = self.create_role_user("Viewer")
        user_id = user.id

        response = self.client.post(
            f"/admin/tables/users/{user_id}/delete", follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(User, user_id))

    def test_admin_cannot_delete_own_account(self):
        response = self.client.post(
            f"/admin/tables/users/{self.user.id}/delete",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("No podés eliminar tu propia cuenta", response.get_data(as_text=True))
        self.assertIsNotNone(db.session.get(User, self.user.id))

    def test_tables_page_lists_database_tables(self):
        html = self.client.get("/admin/tables").get_data(as_text=True)

        self.assertIn("Usuarios", html)
        self.assertIn("Roles", html)
        self.assertIn("<code>notes</code>", html)

    def test_admin_can_browse_table_rows(self):
        html = self.client.get("/admin/tables/roles").get_data(as_text=True)

        self.assertIn("Admin", html)

    def test_admin_can_create_edit_and_delete_table_rows(self):
        response = self.client.post(
            "/admin/tables/roles/new",
            data={"name": "Reviewer"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        role = Role.query.filter_by(name="Reviewer").one()
        role_id = role.id

        response = self.client.post(
            f"/admin/tables/roles/{role_id}/edit",
            data={"name": "Reviewer Updated"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(db.session.get(Role, role_id).name, "Reviewer Updated")

        response = self.client.post(
            f"/admin/tables/roles/{role_id}/delete",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(Role, role_id))

    def test_user_avatar_renders_as_image_in_table(self):
        user = self.create_role_user("Viewer")
        user.avatar = "https://example.com/avatar.png"
        db.session.commit()

        html = self.client.get("/admin/tables/users").get_data(as_text=True)

        self.assertIn(
            '<img class="avatar avatar-sm"', html
        )
        self.assertIn('src="https://example.com/avatar.png"', html)

    def test_table_routes_reject_non_admin(self):
        viewer = self.create_role_user("Viewer")
        self.login(viewer)

        self.assertEqual(self.client.get("/admin/tables").status_code, 403)
        self.assertEqual(self.client.get("/admin/tables/roles").status_code, 403)

    def test_admin_can_edit_user_from_table_editor(self):
        user = self.create_role_user("Viewer")
        original_password = user.password

        response = self.client.get(f"/admin/tables/users/{user.id}/edit")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Contraseña", html)
        self.assertIn('type="file"', html)
        self.assertIn('enctype="multipart/form-data"', html)

        response = self.client.post(
            f"/admin/tables/users/{user.id}/edit",
            data={
                "name": "Renamed User",
                "email": user.email,
                "password": "",
                "role_id": str(user.role_id),
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        updated = db.session.get(User, user.id)
        self.assertEqual(updated.name, "Renamed User")
        self.assertEqual(updated.password, original_password)

    def test_admin_can_upload_user_avatar_from_table_editor(self):
        user = self.create_role_user("Viewer")

        response = self.client.post(
            f"/admin/tables/users/{user.id}/edit",
            data={
                "name": user.name,
                "email": user.email,
                "password": "",
                "role_id": str(user.role_id),
                "avatar": (io.BytesIO(b"fake image bytes"), "avatar.png"),
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        updated = db.session.get(User, user.id)
        self.assertTrue(updated.avatar)
        self.assertIn("/notes/uploads/", updated.avatar)
        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.upload_path,
                    updated.avatar.split("/notes/uploads/", 1)[1],
                )
            )
        )

    def test_table_editor_rejects_invalid_avatar_file(self):
        user = self.create_role_user("Viewer")

        response = self.client.post(
            f"/admin/tables/users/{user.id}/edit",
            data={
                "name": user.name,
                "email": user.email,
                "password": "",
                "role_id": str(user.role_id),
                "avatar": (io.BytesIO(b"not an image"), "avatar.txt"),
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Formato no permitido", response.get_data(as_text=True))
        self.assertIsNone(db.session.get(User, user.id).avatar)

    def test_admin_cannot_demote_self_from_table_editor(self):
        viewer_role = Role.query.filter_by(name="Viewer").first()

        if not viewer_role:
            viewer_role = Role(name="Viewer")
            db.session.add(viewer_role)
            db.session.commit()

        response = self.client.post(
            f"/admin/tables/users/{self.user.id}/edit",
            data={
                "name": self.user.name,
                "email": self.user.email,
                "password": "",
                "role_id": str(viewer_role.id),
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No podés quitarte el rol de administrador",
            response.get_data(as_text=True),
        )
        self.assertEqual(
            db.session.get(User, self.user.id).role.name, "Admin"
        )
