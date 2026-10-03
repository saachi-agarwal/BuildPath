"""
app.py
-------
BuildPath entry point. Run this file to start the app:

    python app.py

It creates the Flask app, initializes the database, seeds the project
catalog (only on first run), and registers all routes.
"""

import os
from flask import Flask
from dotenv import load_dotenv

from models import init_db
from routes import main
import seed_data

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-this")
    app.register_blueprint(main)
    return app


app = create_app()

# Make sure tables exist, then seed the project catalog if it's empty
init_db()
seed_data.seed_if_needed()

if __name__ == "__main__":
    app.run(debug=True)
