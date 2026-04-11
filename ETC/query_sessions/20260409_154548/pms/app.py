"""
PMS (Project Management System) - Application Factory

Creates and configures the Flask application instance.
"""
from flask import Flask
from flask_cors import CORS
from typing import Optional

from config import config
from models import db
from extensions import migrate


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Configuration name (development, testing, production).
                   Uses default if not specified.
    
    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from auth import auth_bp
    from projects import projects_bp
    from api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
