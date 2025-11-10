"""
Routes package
Registers all Flask blueprints for the application
"""

from flask import Blueprint

# Import blueprints
from app.routes.auth import auth_bp
from app.routes.products import products_bp
from app.routes.cart import cart_bp
from app.routes.orders import orders_bp
from app.routes.admin import admin_bp
from app.routes.files import files_bp


def register_blueprints(app):
    """
    Register all blueprints with the Flask application
    
    Args:
        app: Flask application instance
    """
    # Public routes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(files_bp, url_prefix='/files')
    
    # Admin routes
    app.register_blueprint(admin_bp, url_prefix='/admin')


__all__ = [
    'auth_bp',
    'products_bp',
    'cart_bp',
    'orders_bp',
    'admin_bp',
    'files_bp',
    'register_blueprints'
]