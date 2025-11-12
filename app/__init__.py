"""
app/__init__.py
Flask Application Factory for Custom Printing Website
"""

import os
import logging
from datetime import datetime
 
from flask import Flask, g
from flask_cors import CORS
from app.config import get_config
from app.database import init_db, close_db, health_check

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """Application factory"""
    app = Flask(__name__)
    config_class = config_class or get_config()
    app.config.from_object(config_class)

    # Validate configuration
    errors = config_class.validate_config()
    if errors:
        for e in errors:
            logger.error(e)
        raise ValueError("Invalid configuration")

    logger.info(f"Starting app with {config_class.__class__.__name__}")

    # Initialize extensions
    init_db(app)
    if app.config.get("CORS_ORIGINS"):
        CORS(app, origins=app.config["CORS_ORIGINS"])

    # Register blueprints
    register_blueprints(app)

    # Error handlers
    register_error_handlers(app)

    # Request handlers
    register_request_handlers(app)

    # Security headers
    apply_security_headers(app)

    # CLI commands
    register_cli_commands(app)

    return app


def register_blueprints(app):
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.products import products_bp
    from app.routes.cart import cart_bp
    from app.routes.orders import orders_bp
    from app.routes.files import files_bp
    from app.routes.customer import customer_bp

    app.register_blueprint(main_bp, url_prefix="/")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(files_bp, url_prefix="/files")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        return {"error": "Internal server error"}, 500


def register_request_handlers(app):
    @app.before_request
    def before_request():
        g.start_time = datetime.now()

    @app.after_request
    def after_request(response):
        if hasattr(g, "start_time"):
            elapsed = (datetime.now() - g.start_time).total_seconds()
            logger.debug(f"Request completed in {elapsed:.3f}s")
        return response

    @app.teardown_appcontext
    def teardown(exception=None):
        if hasattr(g, "db_conn"):
            close_db()


def apply_security_headers(app):
    @app.after_request
    def set_headers(resp):
        for header, value in app.config.get("SECURITY_HEADERS", {}).items():
            resp.headers[header] = value
        return resp


def register_cli_commands(app):
    @app.cli.command()
    def test_db():
        """Test database connection"""
        status = health_check()
        print(status)

    @app.cli.command()
    def init_database():
        from app.database import execute_sql_file

        files = [
            "database/01_schema.sql",
            "database/02_indexes.sql",
            "database/03_functions.sql",
            "database/04_triggers.sql",
            "database/05_views.sql",
        ]
        for f in files:
            if os.path.exists(f):
                execute_sql_file(f)
                print(f"{f} executed")
            else:
                print(f"{f} not found")


# Create app instance
app = create_app()


# Cleanup on exit
import atexit

@atexit.register
def shutdown():
    logger.info("Shutting down...")
    close_db()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
