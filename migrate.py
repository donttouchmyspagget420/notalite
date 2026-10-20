import sys
from sqlalchemy import create_engine,inspect,text
from models import db

engine = create_engine("sqlite:///instance/database.db")

def init():
    db.metadata.create_all(bind=engine)
    print("Database tables initialized.")

def clear():
    db.metadata.drop_all
    print("Database dropped")

def check():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if not table_names:
        print("No tables found in the database.")
        return

    with engine.connect() as conn:
        for table_name in table_names:
            print(f"\n================ TABLE: {table_name} ================")
            
            # Execute direct raw SELECT
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            
            # Get column names directly from SQL cursor metadata
            columns = result.keys()
            print(f"COLUMNS: {list(columns)}")
            print("-" * 50)

            rows = result.fetchall()
            if not rows:
                print("(0 rows)")
                continue

            for row in rows:
                # row._mapping displays column_name: value pairs like a database shell output
                print(dict(row._mapping))

if len(sys.argv) <= 0:
    sys.exit("no bastante argumentos")

command = sys.argv[1]

match command:
    case "init":
        init()
    case "clear":
        clear()
    case "check":
        check()
