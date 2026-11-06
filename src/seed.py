import random
from datetime import timezone

from faker import Faker
from flask_bcrypt import generate_password_hash

from src.extensions import db
from src.models import Collab, Directory, Note, Role, Tag, User

fake = Faker()


def seed_database():
    print("Resetting database schema...")
    db.drop_all()
    db.create_all()

    print("Seeding Roles...")
    roles_data = ['Admin', 'Editor', 'Viewer']
    roles = []
    for role_name in roles_data:
        role = Role(name=role_name)
        db.session.add(role)
        roles.append(role)
    db.session.commit()

    print("Seeding Users...")
    users = []
    default_password_hash = generate_password_hash("Password123!")

    for _ in range(10):
        user = User(
            name=fake.name(),
            email=fake.unique.email(),
            password=default_password_hash,
            avatar=fake.image_url(width=200, height=200),
            role=random.choice(roles)
        )
        db.session.add(user)
        users.append(user)
    db.session.commit()

    print("Seeding Directories...")
    directories = []
    for user in users:
        root_dir = Directory(
            name="Root",
            user=user,
            parent=None
        )
        db.session.add(root_dir)
        directories.append(root_dir)

        for _ in range(random.randint(2, 4)):
            sub_dir = Directory(
                name=fake.word().capitalize(),
                user=user,
                parent=random.choice([root_dir, None])
            )
            db.session.add(sub_dir)
            directories.append(sub_dir)
    db.session.commit()

    print("Seeding Notes...")
    notes = []
    for user in users:
        user_dirs = [d for d in directories if d.user == user]
        
        for _ in range(random.randint(3, 6)):
            created_dt = fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)
            is_deleted = fake.boolean(chance_of_getting_true=15)

            note = Note(
                title=fake.sentence(nb_words=4).rstrip('.'),
                name=f"{fake.word().lower()}.md",
                content=fake.paragraph(nb_sentences=5),
                created_at=created_dt,
                modified_at=created_dt,
                deleted_at=fake.date_time_between(start_date=created_dt, end_date="now", tzinfo=timezone.utc) if is_deleted else None,
                to_delete=is_deleted,
                user=user,
                directory=random.choice(user_dirs)
            )
            db.session.add(note)
            notes.append(note)
    db.session.commit()

    print("Seeding Collaborations (Collabs)...")
    existing_collabs = set()
    for note in notes:
        potential_collaborators = [u for u in users if u != note.user]
        num_collabs = random.randint(0, min(2, len(potential_collaborators)))
        
        selected_users = random.sample(potential_collaborators, num_collabs)
        for col_user in selected_users:
            pair = (col_user, note)
            if pair not in existing_collabs:
                existing_collabs.add(pair)
                collab = Collab(
                    permission=random.choice(["view", "edit"]),
                    user=col_user,
                    note=note
                )
                db.session.add(collab)
    db.session.commit()

    print("Seeding Tags...")
    tag_names = ["Work", "Personal", "Ideas", "Important", "Archive", "Project"]
    tags = []
    for name in tag_names:
        tag = Tag(
            nombre=name,
            color=fake.hex_color()
        )
        db.session.add(tag)
        tags.append(tag)
    db.session.commit()

    print("Assigning tags to notes...")
    for note in notes:
        note.tags = random.sample(tags, random.randint(0, 3))
    db.session.commit()

    print("Database successfully seeded!")
