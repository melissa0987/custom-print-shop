"""
Decorators Module
Authentication and authorization decorators for route protection 
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for, request, flash, current_app
import logging

logger = logging.getLogger(__name__)


def login_required(f):
    """
    Decorator to require customer authentication
    
    Usage:
        @app.route('/profile')
        @login_required
        def profile():
            return "User profile"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            # Check if request expects JSON
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Authentication required'}), 401
            else:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin authentication
    
    Usage:
        @app.route('/admin/dashboard')
        @admin_required
        def admin_dashboard():
            return "Admin dashboard"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            # Check if request expects JSON
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Admin authentication required'}), 401
            else:
                flash('Admin access required', 'danger')
                return redirect(url_for('auth.admin_login', next=request.url))
        
        return f(*args, **kwargs)
    
    return decorated_function


def role_required(*roles):
    """
    Decorator to require specific admin roles
    
    Args:
        *roles: One or more role names ('super_admin', 'admin', 'staff')
    
    Usage:
        @app.route('/admin/users')
        @role_required('super_admin', 'admin')
        def manage_users():
            return "User management"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Admin authentication required'}), 401
                else:
                    flash('Admin access required', 'danger')
                    return redirect(url_for('auth.admin_login'))
            
            # Check admin role using psycopg2 model
            try:
                from app.models.admin_user import AdminUser
                
                admin_model = AdminUser()
                admin = admin_model.get_by_id(session['admin_id'])
                
                if not admin or not admin.get('is_active'):
                    session.clear()
                    if request.is_json or request.accept_mimetypes.accept_json:
                        return jsonify({'error': 'Admin account is inactive'}), 403
                    else:
                        flash('Admin account is inactive', 'danger')
                        return redirect(url_for('auth.admin_login'))
                
                if admin.get('role') not in roles:
                    if request.is_json or request.accept_mimetypes.accept_json:
                        return jsonify({'error': 'Insufficient permissions'}), 403
                    else:
                        flash('You do not have permission to access this page', 'danger')
                        return redirect(url_for('admin.dashboard'))
            
            except Exception as e:
                logger.error(f"Authorization error: {e}")
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': f'Authorization failed: {str(e)}'}), 500
                else:
                    flash('Authorization error', 'danger')
                    return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def super_admin_required(f):
    """
    Decorator to require super admin role
    Shorthand for @role_required('super_admin')
    
    Usage:
        @app.route('/admin/create-admin')
        @super_admin_required
        def create_admin():
            return "Create new admin"
    """
    return role_required('super_admin')(f)


def permission_required(permission):
    """
    Decorator to require specific admin permission
    
    Args:
        permission (str): Permission name (e.g., 'add_product', 'update_order_status')
    
    Usage:
        @app.route('/admin/products/delete/<int:id>')
        @permission_required('add_product')
        def delete_product(id):
            return "Delete product"
    
    Note: Uses the has_permission() static method from AdminUser model
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Admin authentication required'}), 401
                else:
                    flash('Admin access required', 'danger')
                    return redirect(url_for('auth.admin_login'))
            
            try:
                from app.models.admin_user import AdminUser
                
                admin_model = AdminUser()
                admin = admin_model.get_by_id(session['admin_id'])
                
                if not admin or not admin.get('is_active'):
                    session.clear()
                    if request.is_json or request.accept_mimetypes.accept_json:
                        return jsonify({'error': 'Admin account is inactive'}), 403
                    else:
                        flash('Admin account is inactive', 'danger')
                        return redirect(url_for('auth.admin_login'))
                
                # Check permission using static method
                if not AdminUser.has_permission(admin, permission):
                    if request.is_json or request.accept_mimetypes.accept_json:
                        return jsonify({'error': f'Permission denied: {permission}'}), 403
                    else:
                        flash(f'You do not have permission: {permission}', 'danger')
                        return redirect(url_for('admin.dashboard'))
            
            except Exception as e:
                logger.error(f"Authorization error: {e}")
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': f'Authorization failed: {str(e)}'}), 500
                else:
                    flash('Authorization error', 'danger')
                    return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def guest_or_customer(f):
    """
    Decorator that allows both guest and authenticated customers
    Creates a session ID for guests if not present
    
    Usage:
        @app.route('/cart/add')
        @guest_or_customer
        def add_to_cart():
            # Can use session['customer_id'] or session['session_id']
            return "Add to cart"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import uuid
        
        # If not logged in, ensure guest has a session ID
        if 'customer_id' not in session and 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
        
        return f(*args, **kwargs)
    
    return decorated_function


def json_required(f):
    """
    Decorator to require JSON content type
    
    Usage:
        @app.route('/api/data', methods=['POST'])
        @json_required
        def api_endpoint():
            data = request.get_json()
            return jsonify(data)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(max_requests=10, window_seconds=60):
    """
    Simple rate limiting decorator (basic implementation)
    For production, use Flask-Limiter or Redis-based solution
    
    Args:
        max_requests (int): Maximum requests allowed
        window_seconds (int): Time window in seconds
    
    Usage:
        @app.route('/api/sensitive')
        @rate_limit(max_requests=5, window_seconds=60)
        def sensitive_endpoint():
            return "Limited endpoint"
    
    Note: This is a simple in-memory implementation. For production with 
    multiple workers, use Flask-Limiter with Redis backend.
    """
    def decorator(f):
        # Store request timestamps per user/IP
        request_history = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from datetime import datetime, timedelta
            
            # Get identifier (user_id or IP address)
            identifier = session.get('customer_id') or session.get('admin_id') or request.remote_addr
            
            current_time = datetime.now()
            
            # Initialize history for this identifier
            if identifier not in request_history:
                request_history[identifier] = []
            
            # Remove old requests outside the time window
            cutoff_time = current_time - timedelta(seconds=window_seconds)
            request_history[identifier] = [
                timestamp for timestamp in request_history[identifier]
                if timestamp > cutoff_time
            ]
            
            # Check if limit exceeded
            if len(request_history[identifier]) >= max_requests:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': window_seconds
                    }), 429
                else:
                    flash('Too many requests. Please try again later.', 'warning')
                    return redirect(url_for('index')), 429
            
            # Add current request
            request_history[identifier].append(current_time)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def validate_cart_access(f):
    """
    Decorator to validate user has access to the cart
    Expects cart_id in route parameters
    
    Usage:
        @app.route('/cart/<int:cart_id>/update')
        @guest_or_customer
        @validate_cart_access
        def update_cart(cart_id):
            return "Update cart"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cart_id = kwargs.get('cart_id')
        
        if not cart_id:
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Cart ID required'}), 400
            else:
                flash('Invalid cart', 'danger')
                return redirect(url_for('index'))
        
        try:
            from app.models.shopping_cart import ShoppingCart
            
            cart_model = ShoppingCart()
            cart = cart_model.get_by_id(cart_id)
            
            if not cart:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Cart not found'}), 404
                else:
                    flash('Cart not found', 'danger')
                    return redirect(url_for('index'))
            
            # Check if user has access
            customer_id = session.get('customer_id')
            session_id = session.get('session_id')
            
            has_access = False
            if customer_id and cart.get('customer_id') == customer_id:
                has_access = True
            elif session_id and cart.get('session_id') == session_id:
                has_access = True
            
            if not has_access:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Access denied to this cart'}), 403
                else:
                    flash('Access denied', 'danger')
                    return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Cart access validation error: {e}")
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Cart validation failed'}), 500
            else:
                flash('Error validating cart access', 'danger')
                return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_order_access(f):
    """
    Decorator to validate user has access to the order
    Expects order_id in route parameters
    
    Usage:
        @app.route('/orders/<int:order_id>')
        @login_required
        @validate_order_access
        def view_order(order_id):
            return "View order"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        order_id = kwargs.get('order_id')
        
        if not order_id:
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Order ID required'}), 400
            else:
                flash('Invalid order', 'danger')
                return redirect(url_for('index'))
        
        try:
            from app.models.order import Order
            
            order_model = Order()
            order = order_model.get_by_id(order_id)
            
            if not order:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Order not found'}), 404
                else:
                    flash('Order not found', 'danger')
                    return redirect(url_for('index'))
            
            # Check if user has access (customer owns order or is admin)
            customer_id = session.get('customer_id')
            admin_id = session.get('admin_id')
            
            has_access = False
            if admin_id:
                # Admins can access all orders
                has_access = True
            elif customer_id and order.get('customer_id') == customer_id:
                has_access = True
            
            if not has_access:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({'error': 'Access denied to this order'}), 403
                else:
                    flash('Access denied', 'danger')
                    return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Order access validation error: {e}")
            if request.is_json or request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Order validation failed'}), 500
            else:
                flash('Error validating order access', 'danger')
                return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    
    return decorated_function