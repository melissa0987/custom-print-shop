"""
Decorators Module
Authentication and authorization decorators for route protection
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for, request, flash

from app.database import get_db_session
from app.models.__models_init__ import AdminUser


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
            
            # Check admin role
            try:
                with get_db_session() as db_session:
                    admin = db_session.query(AdminUser).filter_by(
                        admin_id=session['admin_id']
                    ).first()
                    
                    if not admin or not admin.is_active:
                        session.clear()
                        if request.is_json or request.accept_mimetypes.accept_json:
                            return jsonify({'error': 'Admin account is inactive'}), 403
                        else:
                            flash('Admin account is inactive', 'danger')
                            return redirect(url_for('auth.admin_login'))
                    
                    if admin.role not in roles:
                        if request.is_json or request.accept_mimetypes.accept_json:
                            return jsonify({'error': 'Insufficient permissions'}), 403
                        else:
                            flash('You do not have permission to access this page', 'danger')
                            return redirect(url_for('admin.dashboard'))
            
            except Exception as e:
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
        permission (str): Permission name (e.g., 'manage_products', 'manage_orders')
    
    Usage:
        @app.route('/admin/products/delete/<int:id>')
        @permission_required('manage_products')
        def delete_product(id):
            return "Delete product"
    
    Note: This requires AdminUser model to have a has_permission() method
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
                with get_db_session() as db_session:
                    admin = db_session.query(AdminUser).filter_by(
                        admin_id=session['admin_id']
                    ).first()
                    
                    if not admin or not admin.is_active:
                        session.clear()
                        if request.is_json or request.accept_mimetypes.accept_json:
                            return jsonify({'error': 'Admin account is inactive'}), 403
                        else:
                            flash('Admin account is inactive', 'danger')
                            return redirect(url_for('auth.admin_login'))
                    
                    # Check permission (super_admin has all permissions)
                    if admin.role == 'super_admin':
                        return f(*args, **kwargs)
                    
                    # Check if admin has specific permission
                    if hasattr(admin, 'has_permission') and admin.has_permission(permission):
                        return f(*args, **kwargs)
                    
                    # Permission denied
                    if request.is_json or request.accept_mimetypes.accept_json:
                        return jsonify({'error': f'Permission denied: {permission}'}), 403
                    else:
                        flash(f'You do not have permission: {permission}', 'danger')
                        return redirect(url_for('admin.dashboard'))
            
            except Exception as e:
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