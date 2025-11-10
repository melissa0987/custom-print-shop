"""
Flask Application Factory for Custom Printing Website
"""

from flask import Flask, g
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Import configuration
from app.config import get_config

# Import database initialization
from app.database import (
    db, migrate, init_db, test_connection, 
    close_connection_pool, get_db_connection, release_db_connection
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """
    Application factory function.
    
    Args:
        config_class: Configuration class to use (optional)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    
    app.config.from_object(config_class)
    
    # Validate configuration
    config_errors = config_class.validate_config()
    if config_errors:
        logger.error("Configuration validation failed:")
        for error in config_errors:
            logger.error(f"  - {error}")
        raise ValueError("Invalid configuration. Check logs for details.")
    
    logger.info(f"Application starting with {config_class.__name__}")
    logger.info(f"Database: {app.config['DATABASE_NAME']} on {app.config['DATABASE_HOST']}")
    
    # Initialize extensions
    init_extensions(app)
    
    # Test database connection
    if not test_connection(app):
        logger.error("Failed to connect to database!")
        raise ConnectionError("Database connection failed")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register request handlers
    register_request_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Apply security headers
    apply_security_headers(app)
    
    logger.info("Application initialization complete")
    
    return app


def init_extensions(app):
    """Initialize Flask extensions"""
    
    # Initialize database
    init_db(app)
    
    # Initialize CORS if needed
    if app.config.get('CORS_ORIGINS'):
        CORS(app, origins=app.config['CORS_ORIGINS'])
        logger.info(f"CORS enabled for origins: {app.config['CORS_ORIGINS']}")
    
    logger.info("Extensions initialized")


def register_blueprints(app):
    """Register Flask blueprints"""
    
    # Import blueprints here to avoid circular imports
    try:
        # Example: Import your route blueprints
        # from app.routes.main import main_bp
        # from app.routes.auth import auth_bp
        # from app.routes.admin import admin_bp
        # from app.routes.products import products_bp
        # from app.routes.cart import cart_bp
        # from app.routes.orders import orders_bp
        
        # Register blueprints
        # app.register_blueprint(main_bp)
        # app.register_blueprint(auth_bp, url_prefix='/auth')
        # app.register_blueprint(admin_bp, url_prefix='/admin')
        # app.register_blueprint(products_bp, url_prefix='/products')
        # app.register_blueprint(cart_bp, url_prefix='/cart')
        # app.register_blueprint(orders_bp, url_prefix='/orders')
        
        logger.info("Blueprints registered (add your blueprints here)")
    except ImportError as e:
        logger.warning(f"Could not import blueprints: {e}")


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error: {error}")
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {error}")
        db.session.rollback()
        return {"error": "Internal server error"}, 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"403 error: {error}")
        return {"error": "Forbidden"}, 403
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        logger.warning(f"401 error: {error}")
        return {"error": "Unauthorized"}, 401
    
    logger.info("Error handlers registered")


def register_request_handlers(app):
    """Register before/after request handlers"""
    
    @app.before_request
    def before_request():
        """Log request and setup request context"""
        g.request_start_time = datetime.utcnow()
        logger.debug(f"Request started: {g.request_start_time}")
    
    @app.after_request
    def after_request(response):
        """Log response and add security headers"""
        if hasattr(g, 'request_start_time'):
            elapsed = (datetime.utcnow() - g.request_start_time).total_seconds()
            logger.debug(f"Request completed in {elapsed:.3f}s")
        
        return response
    
    @app.teardown_appcontext
    def teardown_db(exception=None):
        """Clean up database connections"""
        if exception:
            logger.error(f"Request teardown with exception: {exception}")
        
        # Release any psycopg2 connections stored in g
        if hasattr(g, 'db_conn'):
            release_db_connection(g.db_conn)
            delattr(g, 'db_conn')
    
    logger.info("Request handlers registered")


def apply_security_headers(app):
    """Apply security headers to all responses"""
    
    @app.after_request
    def set_security_headers(response):
        """Add security headers to response"""
        for header, value in app.config['SECURITY_HEADERS'].items():
            response.headers[header] = value
        return response
    
    logger.info("Security headers configured")


def register_cli_commands(app):
    """Register custom CLI commands"""
    
    @app.cli.command()
    def test_db():
        """Test database connection"""
        if test_connection(app):
            print("✓ Database connection successful")
        else:
            print("✗ Database connection failed")
    
    @app.cli.command()
    def init_database():
        """Initialize database tables (for SQLAlchemy models)"""
        from app.database import create_tables
        create_tables(app)
        print("✓ Database tables created")
    
    @app.cli.command()
    def show_config():
        """Show safe configuration"""
        from app.config import Config
        print("\nCurrent Configuration:")
        print("-" * 50)
        for key, value in Config.get_safe_config().items():
            print(f"{key}: {value}")
        print("-" * 50)
    
    logger.info("CLI commands registered")


# Create application instance (for development server)
app = create_app()


# Application shutdown handler
import atexit

@atexit.register
def shutdown():
    """Clean up on application shutdown"""
    logger.info("Application shutting down...")
    close_connection_pool()
    logger.info("Application shutdown complete")


if __name__ == '__main__':
    # This is for development only
    # Use a proper WSGI server like Gunicorn for production
    port = int(os.environ.get('PORT', 5000))
    
    if app.config['DEBUG']:
        logger.warning("Running in DEBUG mode - DO NOT use in production!")
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        logger.info(f"Starting production server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)