"""
app/routes/auth.py
Authentication Routes
Handles customer and admin authentication (registration, login, logout)
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime, timedelta

from app.models import Customer, AdminUser
from app.models.cart_item import CartItem
from app.models.cart_item_customization import CartItemCustomization
from app.models.shopping_cart import ShoppingCart
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
        
        # Check if email exists
        existing_email = customer_model.get_by_email(data['email'].lower())
        if existing_email:
            error_msg = 'Email already exists'
            if request.is_json:
                return jsonify({'error': error_msg}), 409
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))
        
        # Store guest session_id before registration
        guest_session_id = session.get('session_id')
        
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
        
        # Merge guest cart if exists
        if guest_session_id:
            merge_guest_cart_to_user(customer['customer_id'])
        
        # Check if user has items in cart after merge
        from app.routes.cart import get_or_create_cart, update_cart_count
        cart = get_or_create_cart()
        update_cart_count()
        
        has_cart_items = False
        if cart:
            from app.models.cart_item import CartItem
            cart_item_model = CartItem()
            cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
            has_cart_items = len(cart_items) > 0
        
        if request.is_json:
            return jsonify({
                'message': 'Registration successful', 
                'customer': customer,
                'redirect': url_for('orders.checkout') if has_cart_items else url_for('main.homepage')
            }), 201
        
        flash('Registration successful! Welcome to PrintCraft.', 'success')
        
        # Redirect to checkout if cart has items, otherwise to homepage
        if has_cart_items:
            flash('Your cart items have been saved. You can now proceed to checkout.', 'success')
            return redirect(url_for('orders.checkout'))
        else:
            return redirect(url_for('main.homepage'))
            
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
        merge_guest_cart_to_user(customer['customer_id'])

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



def merge_guest_cart_to_user(customer_id):
    """Merge guest cart items into logged-in user's cart"""
    if 'session_id' not in session:
        return

    session_id = session['session_id']
    cart_model = ShoppingCart()
    cart_item_model = CartItem()
    customization_model = CartItemCustomization()

    try:
        # Get guest cart
        guest_carts = cart_model.get_by_session(session_id)
        if not guest_carts:
            return
        guest_cart = guest_carts[0]

        # Get user cart (or create if none)
        user_carts = cart_model.get_by_customer(customer_id)
        now = datetime.now()
        if user_carts:
            # Find active cart
            user_cart = None
            for cart in user_carts:
                if cart.get('expires_at') and cart['expires_at'] > now:
                    user_cart = cart
                    break
            
            # If no active cart, create one
            if not user_cart:
                cart_id = cart_model.create(
                    customer_id=customer_id,
                    expires_at=now + timedelta(days=30)
                )
                user_cart = cart_model.get_by_id(cart_id)
        else:
            cart_id = cart_model.create(
                customer_id=customer_id,
                expires_at=now + timedelta(days=30)
            )
            user_cart = cart_model.get_by_id(cart_id)

        # Merge guest cart items
        guest_items = cart_item_model.get_by_cart(guest_cart['shopping_cart_id'])
        user_items = cart_item_model.get_by_cart(user_cart['shopping_cart_id'])
        user_item_map = {item['product_id']: item for item in user_items}

        for item in guest_items:
            if item['product_id'] in user_item_map:
                # Increment quantity if product exists in user cart
                existing_item = user_item_map[item['product_id']]
                new_qty = existing_item['quantity'] + item['quantity']
                cart_item_model.update(existing_item['cart_item_id'], quantity=new_qty)
            else:
                # Move item to user cart
                new_item_id = cart_item_model.create(
                    shopping_cart_id=user_cart['shopping_cart_id'],
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    design_file_url=item.get('design_file_url')
                )
                # Move customizations if any
                if item.get('customizations'):
                    for c in item['customizations']:
                        customization_model.create(
                            cart_item_id=new_item_id,
                            customization_key=c['customization_key'],
                            customization_value=c['customization_value']
                        )

        # Update uploaded files to link to customer
        from app.models.uploaded_file import UploadedFile
        uploaded_file_model = UploadedFile()
        uploaded_file_model.update_session_to_customer(session_id, customer_id)

        # Delete guest cart items and cart
        for item in guest_items:
            cart_item_model.delete(item['cart_item_id'])
        cart_model.delete(guest_cart['shopping_cart_id'])

        # Remove session_id from session
        session.pop('session_id', None)

        # Update cart count
        session['cart_count'] = cart_item_model.get_total_items(user_cart['shopping_cart_id'])
        
    except Exception as e:
        print(f"Error merging guest cart: {str(e)}")
        # Don't fail registration if cart merge fails
        pass