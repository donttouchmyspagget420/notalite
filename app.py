import os

from src import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("APP_HOST"),
        port=os.getenv("APP_PORT"),
        debug=os.getenv("APP_DEBUG"),
    )
