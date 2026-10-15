import os
from pathlib import Path
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Guarantee loading of root .env file relative to backend/
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Global unbound SQLAlchemy singleton
db = SQLAlchemy()

def init_db(app):
    """
    Configures database engine options and binds SQLAlchemy to the active Flask app context.
    """
    # Required, no fallback: see backend/config.py database_url().
    from backend.config import database_url as required_database_url
    database_url = required_database_url()

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configure connection pooling only for persistent network databases (e.g. Postgres)
    if not database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        }
    
    db.init_app(app)

def get_db_connection():
    """Returns a raw DBAPI connection from the active SQLAlchemy connection pool."""
    return db.engine.raw_connection()