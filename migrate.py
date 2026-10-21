import os
import sys
from sqlalchemy import create_engine,inspect,text
from models import db
from seed import seed_database
from dotenv import load_dotenv

load_dotenv()

DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")

if not DATABASE_URI:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URI)

def seed():
    seed_database()

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
                
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                
                if not rows:
                    print("(0 rows)")
                    continue
                    
                columns = list(result.keys())
                data = [[str(val) if val is not None else "NULL" for val in row] for row in rows]
                
                # Calculate maximum width for each column (accounting for header lengths)
                col_widths = [
                    max(len(col), max(len(row[i]) for row in data))
                    for i, col in enumerate(columns)
                ]
                
                # Build layout formats
                header_str = " | ".join(f"{col:<{col_widths[i]}}" for i, col in enumerate(columns))
                divider = "-+-".join("-" * w for w in col_widths)
                
                # Print table
                print(header_str)
                print(divider)
                for row in data:
                    print(" | ".join(f"{val:<{col_widths[i]}}" for i, val in enumerate(row)))


def main():
    if len(sys.argv) <= 1:
        sys.exit("no bastante argumentos")

    command = sys.argv[1]

    match command:
        case "init":
            init()
        case "clear":
            clear()
        case "check":
            check()
        case "seed":
            seed()

if __name__ == '__main__':
    main()
