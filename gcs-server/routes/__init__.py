# gcs-server/routes/__init__.py
"""
GCS Server Routes Package
=========================
Modular Flask blueprint organization for the GCS server.

This package splits the monolithic routes.py into focused modules:
- telemetry_routes: Real-time telemetry endpoints
- command_routes: Drone command endpoints
- config_routes: Configuration management
- origin_routes: GPS origin and elevation
- git_routes: Git status endpoints
- heartbeat_routes: Heartbeat and network status
- show_routes: Show import and management

Usage:
    from routes import register_all_blueprints
    register_all_blueprints(app)

Note: This is for the legacy Flask app. The primary API is FastAPI (app_fastapi.py).
"""

from flask import Blueprint

# Import blueprints from submodules
from .telemetry_routes import telemetry_bp
from .command_routes import command_bp
from .config_routes import config_bp
from .git_routes import git_bp
from .heartbeat_routes import heartbeat_bp

# Export all blueprints
__all__ = [
    'telemetry_bp',
    'command_bp',
    'config_bp',
    'git_bp',
    'heartbeat_bp',
    'register_all_blueprints'
]


def register_all_blueprints(app):
    """
    Register all route blueprints with the Flask app.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(telemetry_bp)
    app.register_blueprint(command_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(git_bp)
    app.register_blueprint(heartbeat_bp)
