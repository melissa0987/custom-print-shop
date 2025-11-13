"""
Customer Routes
Handle profile viewing and updating for logged-in customers
"""

from flask import Blueprint, request, jsonify, session, render_template, flash, redirect, url_for
from app.services import CustomerService,  OrderService
from app.models import  EditProfileForm
from app.utils import login_required

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')


# View customer profile
@customer_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    customer_id = session.get('customer_id')
    customer = CustomerService.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for('main.homepage'))

    stats = OrderService.get_customer_order_stats(customer_id)
    return render_template('auth/profile.html', customer=customer, stats=stats)



@customer_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    customer_id = session.get('customer_id')
    customer = CustomerService.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for('main.homepage'))

    form = EditProfileForm()
    
    if form.validate_on_submit():
        # Check if username changed and is unique
        if form.username.data != customer['username']:
            from app.models.customer import Customer
            existing = Customer().get_by_username(form.username.data)
            if existing:
                flash("Username already taken", "error")
                return render_template('auth/edit_profile.html', form=form, customer=customer)
        
        # Check if email changed and is unique
        if form.email.data != customer['email']:
            from app.models.customer import Customer
            # You'll need to add get_by_email method to Customer model
            existing = Customer().get_by_email(form.email.data)
            if existing:
                flash("Email already taken", "error")
                return render_template('auth/edit_profile.html', form=form, customer=customer)
        
        # Update customer info
        update_data = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'username': form.username.data,
            'phone_number': form.phone.data or None
        }
        
        # Handle password change if provided
        if form.password.data:
            if form.password.data != form.confirm_password.data:
                flash("Passwords do not match", "error")
                return render_template('auth/edit_profile.html', form=form, customer=customer)
            
            from werkzeug.security import generate_password_hash
            update_data['password_hash'] = generate_password_hash(form.password.data)
        
        success, result = CustomerService.update_profile(customer_id, **update_data)
        if success:
            # Update session username if changed
            if form.username.data != customer['username']:
                session['username'] = form.username.data
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('customer.profile'))
        else:
            flash(result, "error")
    
    # Pre-populate form with current data on GET request
    if request.method == 'GET':
        form.first_name.data = customer['first_name']
        form.last_name.data = customer['last_name']
        form.email.data = customer['email']
        form.username.data = customer['username']
        form.phone.data = customer.get('phone_number')

    return render_template('auth/edit_profile.html', form=form, customer=customer)

# Change password
@customer_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    customer_id = session.get('customer_id')
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Both current and new password are required'}), 400

    success, result = CustomerService.change_password(customer_id, current_password, new_password)
    if not success:
        return jsonify({'error': result}), 400

    return jsonify({'message': result}), 200 


# Change Password page
@customer_bp.route('/profile/change-password-page', methods=['GET'])
@login_required
def change_password_page():
    return render_template('auth/change_password.html')
