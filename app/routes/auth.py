"""
app/routes/auth.py
Authentication Routes
Handles customer and admin authentication (registration, login, logout)

"""
# TODO: use render_template for html

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
 

from app.models import Customer, AdminUser
from app.utils import (
    login_required, 
    admin_required, 
    permission_required,
    Validators
)
from app.services.auth_service import AuthService

# Create blueprint
auth_bp = Blueprint('auth', __name__)


# ============================================
# CUSTOMER AUTHENTICATION ROUTES
# ============================================
# Customer registration
@auth_bp.route('/register', methods=['GET', 'POST'])
def register(): 
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    # POST request - handle registration
    data = request.get_json() or request.form.to_dict()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            error_msg = f'{field} is required'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))
    
    # Validate username format
    if not Validators.validate_username(data['username']):
        error_msg = 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))
    
    # Validate email format
    if not Validators.validate_email(data['email']):
        error_msg = 'Invalid email format'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))
    
    # Validate password strength
    is_valid, message = Validators.validate_password_strength(data['password'])
    if not is_valid:
        if request.is_json:
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for('auth.register'))
    
    try:
        customer_model = Customer()
        
        # Check if username already exists
        existing_user = customer_model.get_by_username(data['username'].lower())
        if existing_user:
            error_msg = 'Username already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 409
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))
        
        # Create new customer
        customer_id = customer_model.create(
            username=data['username'].lower(),
            email=data['email'].lower(),
            password_hash=generate_password_hash(data['password']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data.get('phone_number'),
            is_active=True
        )
        
        # Get the created customer
        customer = customer_model.get_by_id(customer_id)
        
        # Set session
        session['customer_id'] = customer['customer_id']
        session['username'] = customer['username']
        session.permanent = True
        
        if request.is_json:
            return jsonify({
                'message': 'Registration successful',
                'customer': customer
            }), 201
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('main.home'))
            
    except Exception as e:
        error_msg = f'Registration failed: {str(e)}'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))
    

# Customer login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login(): 
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    data = request.get_json() or request.form.to_dict()
    username_or_email = data.get('username_or_email')
    password = data.get('password')
    
    if not username_or_email or not password:
        error_msg = 'Username/email and password are required'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.login'))
    
    try:
        customer_model = Customer()
        customer = customer_model.get_by_username(username_or_email.lower())
        
        if not customer or not check_password_hash(customer['password_hash'], password):
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
            return redirect(url_for('auth.login'))
        
        if not customer.get('is_active'):
            error_msg = 'Account is inactive'
            if request.is_json:
                return jsonify({'error': error_msg}), 403
            flash(error_msg, 'error')
            return redirect(url_for('auth.login'))
        
        # Update last login
        customer_model.update(customer['customer_id'], last_login=datetime.now())
        
        # Set session
        session['customer_id'] = customer['customer_id']
        session['username'] = customer['username']
        session.permanent = True
        
        if request.is_json:
            return jsonify({
                'message': 'Login successful',
                'customer': customer
            }), 200
        flash('Login successful!', 'success')
        return redirect(url_for('main.home'))
    
    except Exception as e:
        error_msg = f'Login failed: {str(e)}'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('auth.login'))

# Customer logout
@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout(): 
    session.clear()
    
    if request.is_json:
        return jsonify({'message': 'Logout successful'}), 200
    else:
        flash('You have been logged out', 'success')
        return redirect(url_for('auth.login'))


# ============================================
# ADMIN AUTHENTICATION ROUTES
# ============================================

# Admin login
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login(): 
    if request.method == 'GET':
        return render_template('auth/admin_login.html')
    
    # POST request - handle login
    data = request.get_json() or request.form.to_dict()
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    try:
        admin_model = AdminUser()
        
        # Find admin by username
        admin = admin_model.get_by_username(username.lower())
        
        if not admin:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not admin.get('is_active'):
            return jsonify({'error': 'Admin account is inactive'}), 403
        
        # Verify password using static method
        if not AdminUser.verify_password(admin, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        admin_model.update_last_login(admin['admin_id'])
        
        # Set session
        session['admin_id'] = admin['admin_id']
        session['admin_username'] = admin['username']
        session['admin_role'] = admin['role']
        session.permanent = True
        
        return jsonify({
            'message': 'Admin login successful',
            'admin': {
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'email': admin['email'],
                'first_name': admin['first_name'],
                'last_name': admin['last_name'],
                'role': admin['role']
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Admin login failed: {str(e)}'}), 500


# Admin logout
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


# Get current logged-in customer information
@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user(): 
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(session['customer_id'])
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        return jsonify({
            'customer': {
                'customer_id': customer['customer_id'],
                'username': customer['username'],
                'email': customer['email'],
                'first_name': customer['first_name'],
                'last_name': customer['last_name'],
                'phone_number': customer.get('phone_number'),
                'created_at': customer['created_at'].isoformat() if customer.get('created_at') else None,
                'last_login': customer['last_login'].isoformat() if customer.get('last_login') else None
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get user info: {str(e)}'}), 500

# Get current logged-in admin information
@auth_bp.route('/admin/me', methods=['GET'])
@admin_required
def get_current_admin(): 
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(session['admin_id'])
        
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        return jsonify({
            'admin': {
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'email': admin['email'],
                'first_name': admin['first_name'],
                'last_name': admin['last_name'],
                'role': admin['role'],
                'created_at': admin['created_at'].isoformat() if admin.get('created_at') else None,
                'last_login': admin['last_login'].isoformat() if admin.get('last_login') else None
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get admin info: {str(e)}'}), 500


# ============================================
# PASSWORD CHANGE
# ============================================

# Change customer password
@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password(): 
    data = request.get_json()
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400
    
    # Validate new password strength
    is_valid, message = Validators.validate_password(new_password)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(session['customer_id'])
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Verify current password
        if not check_password_hash(customer['password_hash'], current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        customer_model.update(
            customer['customer_id'],
            password_hash=generate_password_hash(new_password)
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


# ============================================
# SESSION CHECK
# ============================================

# Check if user is logged in
@auth_bp.route('/check-session', methods=['GET'])
def check_session(): 
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