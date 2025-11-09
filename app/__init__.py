"""
Flask Application Factory
Creates and configures the Flask application
"""

from flask import Flask, render_template, session
from flask_cors import CORS
import os
from datetime import timedelta

from app.config import Config
from app.database import init_db


def create_app(config_class=Config):
    """
    Application factory pattern
    
    Args:
        config_class: Configuration class (default: Config)
    
    Returns:
        Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Set secret key for sessions
    app.secret_key = app.config['SECRET_KEY']
    
    # Configure session
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    
    # Enable CORS if needed
    if app.config.get('ENABLE_CORS', False):
        CORS(app)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register context processors
    register_context_processors(app)
    
    return app


def register_blueprints(app):
    """Register Flask blueprints"""
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    from app.routes.cart import cart_bp
    from app.routes.orders import orders_bp
    from app.routes.admin import admin_bp
    from app.routes.files import files_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Register home route
    @app.route('/')
    def index():
        """Homepage"""
        return render_template('index.html')


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        # Check if request expects JSON
        from flask import request
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': 'Resource not found'}, 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        from flask import request
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': 'Internal server error'}, 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors"""
        from flask import request
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': 'Access forbidden'}, 403
        return render_template('errors/403.html'), 403


def register_template_filters(app):
    """Register custom Jinja2 filters"""
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Format value as currency"""
        try:
            return f"${float(value):.2f}"
        except (ValueError, TypeError):
            return "$0.00"
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%B %d, %Y'):
        """Format datetime"""
        if value is None:
            return ""
        return value.strftime(format)
    
    @app.template_filter('truncate_text')
    def truncate_text_filter(text, length=50):
        """Truncate text to specified length"""
        if text is None:
            return ""
        if len(text) <= length:
            return text
        return text[:length] + '...'


def register_context_processors(app):
    """Register context processors to inject variables into templates"""
    
    @app.context_processor
    def inject_user():
        """Inject current user info into all templates"""
        user_info = {
            'is_authenticated': 'customer_id' in session or 'admin_id' in session,
            'is_admin': 'admin_id' in session,
            'customer_id': session.get('customer_id'),
            'admin_id': session.get('admin_id'),
            'username': session.get('username'),
        }
        return {'current_user': user_info}
    
    @app.context_processor
    def inject_cart_count():
        """Inject cart item count into all templates"""
        from app.services.cart_service import CartService
        
        cart_count = 0
        try:
            if 'customer_id' in session:
                cart_count = CartService.get_cart_item_count(
                    customer_id=session['customer_id']
                )
            elif 'session_id' in session:
                cart_count = CartService.get_cart_item_count(
                    session_id=session['session_id']
                )
        except Exception:
            # If there's an error getting cart count, just return 0
            cart_count = 0
        
        return {'cart_count': cart_count}