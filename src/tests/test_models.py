from src.extensions import db
from src.models import Collab, Directory, Note, Tag
from src.tests.base import BaseTestCase


class ModelCascadeTestCase(BaseTestCase):
    def test_deleting_user_deletes_owned_data(self):
        user = self.create_user(email="cascade@example.com", name="Cascade User")
        directory = Directory(name="Owned", user_id=user.id)
        tag = Tag(nombre="owned", user_id=user.id)
        db.session.add_all([directory, tag])
        db.session.commit()

        note = Note(
            title="Owned note",
            name="owned.md",
            content="Owned",
            user_id=user.id,
            directory_id=directory.id,
        )
        db.session.add(note)
        db.session.commit()

        note_id = note.id
        directory_id = directory.id
        tag_id = tag.id

        db.session.delete(user)
        db.session.commit()

        self.assertIsNone(db.session.get(Note, note_id))
        self.assertIsNone(db.session.get(Directory, directory_id))
        self.assertIsNone(db.session.get(Tag, tag_id))

    def test_deleting_note_deletes_collaborations(self):
        collaborator = self.create_user()
        collab = Collab(
            permission="view",
            user_id=collaborator.id,
            note_id=self.note.id,
        )
        db.session.add(collab)
        db.session.commit()

        collab_id = collab.id

        db.session.delete(self.note)
        db.session.commit()

        self.assertIsNone(db.session.get(Collab, collab_id))
