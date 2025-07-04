from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config
import sqlite3
import os

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Initialize database with schema
    with app.app_context():
        init_database()
    
    # Register blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

def init_database():
    """Initialize database with Kimball star schema"""
    db_path = db.engine.url.database
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')
    
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Check if database is empty (needs initialization)
    needs_init = False
    if not os.path.exists(db_path):
        needs_init = True
    else:
        # Check if tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        if not tables:
            needs_init = True
    
    if needs_init:
        # Execute schema
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()
        
        print("Database initialized with Kimball star schema")