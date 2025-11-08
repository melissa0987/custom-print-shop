"""
Flask application factory
"""
from flask import Flask
from config import config
from database import init_db, close_db_session


def create_app(config_name='development'):
    """
    Create and configure Flask application
    
    Args:
        config_name (str): Configuration name (development, production, testing)
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize database
    init_db(app)
    
    # Register teardown function for database sessions
    app.teardown_appcontext(close_db_session)
    
    # Register blueprints (routes)
    # TODO: Uncomment as routes are created
    # from app.routes import auth, products, cart, orders, admin, files
    # app.register_blueprint(auth.bp)
    # app.register_blueprint(products.bp)
    # app.register_blueprint(cart.bp)
    # app.register_blueprint(orders.bp)
    # app.register_blueprint(admin.bp)
    # app.register_blueprint(files.bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500