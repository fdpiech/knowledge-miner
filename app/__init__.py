"""Flask application factory for Knowledge Corpus Manager."""

from flask import Flask

from app.config import load_config
from app.models import db


def create_app(config_override: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_override: Optional dictionary of config values to override defaults.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    cfg = load_config()
    app.config["SECRET_KEY"] = cfg.get("server", {}).get(
        "secret_key", "kcm-dev-key-change-in-production"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{cfg['database']['path']}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["KCM"] = cfg

    if config_override:
        app.config.update(config_override)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.browse import browse_bp
    from app.routes.search import search_bp
    from app.routes.consolidate import consolidate_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(consolidate_bp)
    app.register_blueprint(admin_bp)

    return app
