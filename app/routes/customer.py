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


# Update customer profile
@customer_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    customer_id = session.get('customer_id')
    data = request.get_json(silent=True) or request.form.to_dict()

    success, result = CustomerService.update_profile(customer_id, **data)
    if not success:
        if request.is_json:
            return jsonify({'error': result}), 400
        flash(result, "error")
        return redirect(url_for('customer.profile'))

    if request.is_json:
        return jsonify({'message': 'Profile updated successfully', 'customer': result}), 200

    flash("Profile updated successfully", "success")
    return redirect(url_for('customer.profile'))


@customer_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    customer_id = session.get('customer_id')
    customer = CustomerService.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for('main.homepage'))

    form = EditProfileForm(obj=customer)
    if form.validate_on_submit():
        # Call your service to update customer info
        CustomerService.update_customer(customer_id, form.data)
        flash("Profile updated successfully!", "success")
        return redirect(url_for('customer.profile'))

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
    return render_template('customer/change_password.html')
