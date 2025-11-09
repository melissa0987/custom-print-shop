"""
Authentication Routes
Handles customer and admin authentication (registration, login, logout)
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
from datetime import datetime

from app.database import get_db_session
from app.models import Customer, AdminUser
from app.utils import login_required, admin_required, validate_email

# Create blueprint
auth_bp = Blueprint('auth', __name__)


# ============================================
# DECORATORS
# ============================================

def login_required(f):
    """Decorator to require customer login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator to require specific admin permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                return jsonify({'error': 'Admin authentication required'}), 401
            
            with get_db_session() as db_session:
                admin = db_session.query(AdminUser).filter_by(
                    admin_id=session['admin_id']
                ).first()
                
                if not admin or not admin.has_permission(permission):
                    return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================
# VALIDATION HELPERS
# ============================================

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format (3-50 chars, alphanumeric, underscore, hyphen)"""
    pattern = r'^[a-z0-9_-]{3,50}$'
    return re.match(pattern, username, re.IGNORECASE) is not None


def validate_password(password):
    """Validate password strength (min 8 chars, at least 1 letter and 1 number)"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Valid"


# ============================================
# CUSTOMER AUTHENTICATION ROUTES
# ============================================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Customer registration
    
    POST JSON:
        - username: string (required)
        - email: string (required)
        - password: string (required)
        - first_name: string (required)
        - last_name: string (required)
        - phone_number: string (optional)
    
    Returns:
        JSON with customer data or error message
    """
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    # POST request - handle registration
    data = request.get_json() or request.form.to_dict()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate username format
    if not validate_username(data['username']):
        return jsonify({
            'error': 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'
        }), 400
    
    # Validate email format
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password strength
    is_valid, message = validate_password(data['password'])
    if not is_valid:
        return jsonify({'error': message}), 400
    
    try:
        with get_db_session() as db_session:
            # Check if username already exists
            existing_user = db_session.query(Customer).filter_by(
                username=data['username'].lower()
            ).first()
            if existing_user:
                return jsonify({'error': 'Username already exists'}), 409
            
            # Check if email already exists
            existing_email = db_session.query(Customer).filter_by(
                email=data['email'].lower()
            ).first()
            if existing_email:
                return jsonify({'error': 'Email already exists'}), 409
            
            # Create new customer
            customer = Customer(
                username=data['username'].lower(),
                email=data['email'].lower(),
                password_hash=generate_password_hash(data['password']),
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_number=data.get('phone_number')
            )
            
            db_session.add(customer)
            db_session.flush()  # Get the customer_id
            
            # Set session
            session['customer_id'] = customer.customer_id
            session['username'] = customer.username
            session.permanent = True
            
            return jsonify({
                'message': 'Registration successful',
                'customer': {
                    'customer_id': customer.customer_id,
                    'username': customer.username,
                    'email': customer.email,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name
                }
            }), 201
            
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Customer login
    
    POST JSON:
        - username_or_email: string (required)
        - password: string (required)
    
    Returns:
        JSON with customer data or error message
    """
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    # POST request - handle login
    data = request.get_json() or request.form.to_dict()
    
    username_or_email = data.get('username_or_email')
    password = data.get('password')
    
    if not username_or_email or not password:
        return jsonify({'error': 'Username/email and password are required'}), 400
    
    try:
        with get_db_session() as db_session:
            # Try to find customer by username or email
            customer = db_session.query(Customer).filter(
                (Customer.username == username_or_email.lower()) |
                (Customer.email == username_or_email.lower())
            ).first()
            
            if not customer:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            if not customer.is_active:
                return jsonify({'error': 'Account is inactive'}), 403
            
            # Verify password
            if not check_password_hash(customer.password_hash, password):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Update last login
            customer.last_login = datetime.now()
            
            # Set session
            session['customer_id'] = customer.customer_id
            session['username'] = customer.username
            session.permanent = True
            
            return jsonify({
                'message': 'Login successful',
                'customer': {
                    'customer_id': customer.customer_id,
                    'username': customer.username,
                    'email': customer.email,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """Customer logout"""
    session.clear()
    
    if request.is_json:
        return jsonify({'message': 'Logout successful'}), 200
    else:
        flash('You have been logged out', 'success')
        return redirect(url_for('auth.login'))


# ============================================
# ADMIN AUTHENTICATION ROUTES
# ============================================

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login
    
    POST JSON:
        - username: string (required)
        - password: string (required)
    
    Returns:
        JSON with admin data or error message
    """
    if request.method == 'GET':
        return render_template('auth/admin_login.html')
    
    # POST request - handle login
    data = request.get_json() or request.form.to_dict()
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    try:
        with get_db_session() as db_session:
            # Find admin by username
            admin = db_session.query(AdminUser).filter_by(
                username=username.lower()
            ).first()
            
            if not admin:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            if not admin.is_active:
                return jsonify({'error': 'Admin account is inactive'}), 403
            
            # Verify password
            if not check_password_hash(admin.password_hash, password):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Update last login
            admin.last_login = datetime.now()
            
            # Set session
            session['admin_id'] = admin.admin_id
            session['admin_username'] = admin.username
            session['admin_role'] = admin.role
            session.permanent = True
            
            return jsonify({
                'message': 'Admin login successful',
                'admin': {
                    'admin_id': admin.admin_id,
                    'username': admin.username,
                    'email': admin.email,
                    'first_name': admin.first_name,
                    'last_name': admin.last_name,
                    'role': admin.role
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Admin login failed: {str(e)}'}), 500


@auth_bp.route('/admin/logout', methods=['POST', 'GET'])
@admin_required
def admin_logout():
    """Admin logout"""
    session.clear()
    
    if request.is_json:
        return jsonify({'message': 'Admin logout successful'}), 200
    else:
        flash('You have been logged out', 'success')
        return redirect(url_for('auth.admin_login'))


# ============================================
# USER INFO ROUTES
# ============================================

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged-in customer information"""
    try:
        with get_db_session() as db_session:
            customer = db_session.query(Customer).filter_by(
                customer_id=session['customer_id']
            ).first()
            
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404
            
            return jsonify({
                'customer': {
                    'customer_id': customer.customer_id,
                    'username': customer.username,
                    'email': customer.email,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone_number': customer.phone_number,
                    'created_at': customer.created_at.isoformat() if customer.created_at else None,
                    'last_login': customer.last_login.isoformat() if customer.last_login else None
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get user info: {str(e)}'}), 500


@auth_bp.route('/admin/me', methods=['GET'])
@admin_required
def get_current_admin():
    """Get current logged-in admin information"""
    try:
        with get_db_session() as db_session:
            admin = db_session.query(AdminUser).filter_by(
                admin_id=session['admin_id']
            ).first()
            
            if not admin:
                return jsonify({'error': 'Admin not found'}), 404
            
            return jsonify({
                'admin': {
                    'admin_id': admin.admin_id,
                    'username': admin.username,
                    'email': admin.email,
                    'first_name': admin.first_name,
                    'last_name': admin.last_name,
                    'role': admin.role,
                    'created_at': admin.created_at.isoformat() if admin.created_at else None,
                    'last_login': admin.last_login.isoformat() if admin.last_login else None
                }
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get admin info: {str(e)}'}), 500
    
 


# ============================================
# PASSWORD CHANGE
# ============================================

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change customer password
    
    POST JSON:
        - current_password: string (required)
        - new_password: string (required)
    
    Returns:
        JSON success message or error
    """
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400
    
    # Validate new password strength
    is_valid, message = validate_password(new_password)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    try:
        with get_db_session() as db_session:
            customer = db_session.query(Customer).filter_by(
                customer_id=session['customer_id']
            ).first()
            
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404
            
            # Verify current password
            if not check_password_hash(customer.password_hash, current_password):
                return jsonify({'error': 'Current password is incorrect'}), 401
            
            # Update password
            customer.password_hash = generate_password_hash(new_password)
            
            return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


# ============================================
# SESSION CHECK
# ============================================

@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'customer_id' in session:
        return jsonify({
            'logged_in': True,
            'user_type': 'customer',
            'customer_id': session['customer_id'],
            'username': session.get('username')
        }), 200
    elif 'admin_id' in session:
        return jsonify({
            'logged_in': True,
            'user_type': 'admin',
            'admin_id': session['admin_id'],
            'username': session.get('admin_username'),
            'role': session.get('admin_role')
        }), 200
    else:
        return jsonify({'logged_in': False}), 200