"""
app/routes/auth.py
Authentication Routes
Handles customer and admin authentication (registration, login, logout)
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime

from app.models import Customer, AdminUser
from app.utils import (
    login_required,
    admin_required,
    PasswordHelper,
    Validators
)
from werkzeug.security import generate_password_hash
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
    
    data = request.get_json(silent=True) or request.form.to_dict()
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            error_msg = f'{field} is required'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))
    
    if not Validators.validate_username(data['username']):
        error_msg = 'Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))
    
    if not Validators.validate_email(data['email']):
        error_msg = 'Invalid email format'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))
    
    is_valid, message = Validators.validate_password_strength(data['password'])
    if not is_valid:
        if request.is_json:
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(url_for('auth.register'))
    
    try:
        customer_model = Customer()
        existing_user = customer_model.get_by_username(data['username'].lower())
        if existing_user:
            error_msg = 'Username already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 409
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))
        
        # Use PasswordHelper for hashing
        password_hash = PasswordHelper.hash_password(data['password'])
        
        customer_id = customer_model.create(
            username=data['username'].lower(),
            email=data['email'].lower(),
            password_hash=password_hash,
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data.get('phone_number'),
            is_active=True
        )
        
        customer = customer_model.get_by_id(customer_id)
        session['customer_id'] = customer['customer_id']
        session['username'] = customer['username']
        session.permanent = True
        
        if request.is_json:
            return jsonify({'message': 'Registration successful', 'customer': customer}), 201
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

    data = request.get_json(silent=True) or request.form.to_dict()
    username_or_email = data.get('username_or_email')
    password = data.get('password')

    if not username_or_email or not password:
        error_msg = 'Username/email and password are required'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return render_template('auth/login.html')

    try:
        customer_model = Customer()
        customer = customer_model.get_by_username(username_or_email.lower())

        # Make sure there is a hash to check
        if not customer or not customer.get('password_hash'):
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')

        # Verify password against stored hash
        if not PasswordHelper.verify_password(customer['password_hash'], password):
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')

        if not customer.get('is_active'):
            error_msg = 'Account is inactive'
            if request.is_json:
                return jsonify({'error': error_msg}), 403
            flash(error_msg, 'error')
            return render_template('auth/login.html')

        customer_model.update(customer['customer_id'], last_login=datetime.now())
        session['customer_id'] = customer['customer_id']
        session['username'] = customer['username']
        session.permanent = True

        if request.is_json:
            return jsonify({'message': 'Login successful', 'customer': customer}), 200

        flash(f'Welcome back, {customer["first_name"]}!', 'success')
        next_page = request.args.get('next') or request.form.get('next') or url_for('main.homepage')
        return redirect(next_page)

    except Exception as e:
        error_msg = f'Login failed: {str(e)}'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
        return render_template('auth/login.html')


# Customer logout
@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.homepage'))

# ============================================
# PASSWORD CHANGE
# ============================================
@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password(): 
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400
    
    is_valid, message = Validators.validate_password(new_password)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(session['customer_id'])
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        if not PasswordHelper.verify_password(customer['password_hash'], current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        customer_model.update(
            customer['customer_id'],
            password_hash=PasswordHelper.hash_password(new_password)
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500
