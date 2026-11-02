import click
from flask.cli import with_appcontext
from sqlalchemy import inspect, text

from src.extensions import db


@click.group("db")
def db_cli():
    """Utilidades de base de datos."""

@db_cli.command("init")
@with_appcontext
def init():
    db.create_all()
    click.echo("Tablas creadas.")


@db_cli.command("clear")
@with_appcontext
def clear():
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
    click.echo("Tablas vaciadas.")


@db_cli.command("seed")
@with_appcontext
def seed():
    from src.seed import seed_database

    seed_database()
    click.echo("Base de datos poblada.")


@db_cli.command("check")
@with_appcontext
def check():
    table_names = inspect(db.engine).get_table_names()

    if not table_names:
        print("No tables found in the database.")
        return

    with db.engine.connect() as conn:
        for table_name in table_names:
            print(f"\n================ TABLE: {table_name} ================")

            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()

            if not rows:
                print("(0 rows)")
                continue

            columns = list(result.keys())
            data = [
                [str(val) if val is not None else "NULL" for val in row]
                for row in rows
            ]

            col_widths = [
                max(len(col), max(len(row[i]) for row in data))
                for i, col in enumerate(columns)
            ]

            header_str = " | ".join(
                f"{col:<{col_widths[i]}}" for i, col in enumerate(columns)
            )
            divider = "-+-".join("-" * w for w in col_widths)

            print(header_str)
            print(divider)
            for row in data:
                print(
                    " | ".join(
                        f"{val:<{col_widths[i]}}" for i, val in enumerate(row)
                    )
                )


def init_app(app):
    app.cli.add_command(db_cli)
