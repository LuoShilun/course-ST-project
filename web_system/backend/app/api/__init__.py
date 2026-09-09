from __future__ import annotations

from flask import Flask

from app.api.announcements import bp as announcements_bp
from app.api.assistant import bp as assistant_bp
from app.api.auth import bp as auth_bp
from app.api.dashboard import bp as dashboard_bp
from app.api.detection import bp as detection_bp
from app.api.detection import bp_v1_compat as detection_bp_v1_compat
from app.api.health import bp as health_bp
from app.api.records import bp as records_bp
from app.api.robots import bp as robots_bp
from app.api.users import bp as users_bp
from app.api.weather import bp as weather_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(robots_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(detection_bp_v1_compat)
    app.register_blueprint(assistant_bp)
