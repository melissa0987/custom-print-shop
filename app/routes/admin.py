"""
app/routes/admin.py
Admin Routes
Handles admin panel operations (orders, products, customers, reports) 
"""

import traceback
from flask import Blueprint, current_app, flash, redirect, request, jsonify, session, url_for, render_template

from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)
from app.services.admin_service import AdminService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.utils import admin_required, permission_required
from datetime import datetime

from app.utils.decorators import validate_order_access
from app.utils.helpers import DateHelper, PaginationHelper, PriceHelper, StringHelper
from app.utils.image_helpers import ImageHelper
import os
from werkzeug.utils import secure_filename 

 
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================
# ADMIN LOGIN
# ============================================ 
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login(): 
    if session.get('admin_id'):
        return redirect(url_for('admin.get_dashboard'))
      
    if request.method == 'GET':
        return render_template('admin/admin_login.html')

    # Get form data
    data = request.get_json(silent=True) or request.form.to_dict()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        error_msg = 'Email and password are required'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')

    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_email(email.lower())

        print("DEBUG: admin fetched from DB:", admin)
        print("DEBUG: admin type:", type(admin))

        # Check if admin exists
        if not admin:
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

         
        if not AdminUser.verify_password(admin, password):
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Check if active
        if not admin.get('is_active', True):
            error_msg = 'Admin account is inactive. Please contact support.'
            if request.is_json:
                return jsonify({'error': error_msg}), 403
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Update last login
        admin_model.update_last_login(admin['admin_id'])

        # Store admin info in session
        session['admin_id'] = admin['admin_id']
        session['admin_username'] = admin['username']
        session['admin_role'] = admin.get('role', 'staff')
        session['admin_email'] = admin['email']
        session['admin_first_name'] = admin.get('first_name', '')
        
        # Get permissions for this admin
        permissions = admin_model.get_permissions(admin['admin_id'])
        session['permissions'] = permissions
        session.permanent = True

        # Log activity
        try:
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=admin['admin_id'],
                action='login',
                table_name='admin_users',
                record_id=admin['admin_id'],
                old_values=None,
                new_values={'status': 'success', 'timestamp': datetime.now().isoformat()}
            )
        except Exception as log_error:
            print(f"Warning: Failed to log admin activity: {log_error}")

        flash(f'Welcome back, {admin.get("first_name", admin["username"])}!', 'success')
        
        # Handle redirect
        next_page = request.args.get('next') or request.form.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin.get_dashboard'))

    except Exception as e:
        import traceback
        error_msg = f'Login failed: {str(e)}'
        print("DEBUG: Full error traceback:")
        print(traceback.format_exc())
        
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')


# ============================================
# DASHBOARD - HTML PAGE
# ============================================ 
@admin_bp.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('main.homepage'))



@admin_bp.route('/dashboard', methods=['GET'])
@permission_required('view_dashboard')
def get_dashboard():
    stats = AdminService.get_dashboard_stats()

    if not stats:
        # If fetching stats failed, render error page
        return render_template('errors/error.html', message="Failed to load dashboard stats"), 500

    return render_template(
        'admin/admin_dashboard.html',
        stats=stats,
        recent_orders=stats.get('recent_orders', [])
    )


# ============================================
# ORDER MANAGEMENT
# ============================================
@admin_bp.route('/orders', methods=['GET'])
@permission_required('view_orders')
def get_orders():
    status_filter = request.args.get('status')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    try:
        orders, total_orders, total_pages = AdminService.get_all_orders(
            status_filter=status_filter,
            page=page,
            per_page=per_page,
            search_term=search_term
        )

        pagination = {
            'page': page,
            'per_page': per_page,
            'total_orders': total_orders,
            'total_pages': max(1, total_pages),
            'has_next': page * per_page < total_orders,
            'has_prev': page > 1
        }

        return render_template(
            'admin/admin_orders.html',
            orders=orders,
            pagination=pagination
        )

    except Exception as e:
        # Log the error
        print(f"Error in get_orders: {str(e)}")
        print(traceback.format_exc())

        return render_template('errors/error.html', error_message=f'Failed to load orders: {str(e)}'), 500
    
 
@admin_bp.route('/orders/<int:order_id>', methods=['GET'])
@permission_required('view_orders')
def get_order_details(order_id):
    try:
        order_data = AdminService.get_order_details(order_id)

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'order': order_data}), 200

        return render_template('admin/admin_order_detail.html', order=order_data)

    except Exception as e:
        print(f"Error in get_order_details route: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return render_template('errors/error.html', error_message=str(e)), 500


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@permission_required('update_order_status')
def update_order_status(order_id):
    try:
        new_status = request.form.get('status')
        notes = request.form.get('notes', '')

        OrderService.update_order_status(
            order_id=order_id,
            new_status=new_status,
            admin_id=session['admin_id'],
            notes=notes
        )

        flash(f'Status updated to {new_status}', 'success')
        return redirect(url_for('admin.get_order_details', order_id=order_id))

    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return render_template('errors/error.html', error_message=str(e)), 500
    

# ============================================
# PRODUCT MANAGEMENT
# ============================================
@admin_bp.route('/products', methods=['GET'])
@permission_required('view_products')
def get_products_admin():
    try:
        wants_json = request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']

        category_id = request.args.get('category_id', type=int)
        search_term = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')

        data = AdminService.get_products(
            category_id=category_id,
            search_term=search_term,
            min_price=min_price,
            max_price=max_price,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if wants_json:
            return jsonify({'products': data['products'], 'pagination': data['pagination']}), 200

        return render_template(
            'admin/admin_products.html',
            products=data['products'],
            pagination=data['pagination'],
            categories=data['categories'],
            current_category=category_id,
            search_term=search_term,
            sort_by=sort_by,
            sort_order=sort_order
        )

    except Exception as e:
        print(f"Error in get_products_admin: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return render_template('errors/error.html', error_message=str(e)), 500
    
 
@admin_bp.route('/products/create', methods=['GET', 'POST'])
@permission_required('manage_products')
def create_product():
    """Create new product with image"""
    if request.method == 'GET':
        try:
            categories = Category().get_all()
            return render_template('admin/admin_product_form.html', categories=categories, action='create')
        except Exception as e:
            return render_template('errors/error.html', error_message=f"Failed to load form: {str(e)}"), 500

    # POST
    data = request.form.to_dict()
    file = request.files.get('product_image')

    try:
        AdminService.create_product(data, file)
        flash('Product created successfully', 'success')
        return redirect(url_for('admin.get_products_admin'))

    except Exception as e:
        return render_template('errors/error.html', error_message=f"Failed to create product: {str(e)}"), 500
    


@admin_bp.route('/products/<int:product_id>', methods=['GET'])
@permission_required('view_products')
def get_product_detail(product_id): 
    try:
        result = AdminService.get_product_detail(product_id)
        return render_template(
            'admin/admin_product_detail.html',
            product=result['product'],
            categories=result['categories']
        )
    except Exception as e:
        return render_template('errors/error.html', error_message=f"Failed to load product details: {str(e)}"), 500
    

@admin_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@permission_required('manage_products')
def toggle_product_status(product_id):
    """Toggle product active status (deactivate/activate)"""
    try:
        new_status = AdminService.toggle_product_status(product_id, session.get('admin_id'))
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Product {status_text} successfully', 'success')
        return redirect(url_for('admin.get_products_admin'))
    except Exception as e:
        return render_template('errors/error.html', error_message=f'Failed to toggle product status: {str(e)}'), 500
    

@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@permission_required('manage_products')
def delete_product(product_id):
    """Delete product: soft or hard delete depending on related orders"""
    try:
        message = AdminService.delete_product(product_id, session.get('admin_id'))
        flash(message, 'success')
        return redirect(url_for('admin.get_products_admin'))
    except Exception as e:
        return render_template('errors/error.html', error_message=f'Failed to delete product: {str(e)}'), 500


@admin_bp.route('/products/<int:product_id>', methods=['POST'])
@permission_required('manage_products')
def update_product(product_id):
    """Update existing product"""
    try:
        AdminService.update_product(product_id, request.form.to_dict(), 
                                    request.files.get('product_image'), session.get('admin_id'))
        flash('Product updated successfully', 'success')
        return redirect(url_for('admin.get_product_detail', product_id=product_id))
    
    except Exception as e:
        return render_template('errors/error.html', error_message=f'Failed to update product: {str(e)}'), 500
 
# ============================================
# CUSTOMER MANAGEMENT
# ============================================
@admin_bp.route('/customers', methods=['GET'])
@permission_required('view_customers')
def get_customers_admin():
    """Render customers management page with totals and optional filters/sorting"""
    status_filter = request.args.get('status')  # 'active', 'inactive', or None
    search_term = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')

    try:
        customer_model = Customer()
        order_model = Order()

        customers = customer_model.get_all()

        # Compute totals for each customer
        formatted_customers = []
        for c in customers:
            orders = order_model.get_by_customer(c['customer_id'])
            total_orders = len(orders)
            total_spent = sum(order['total_amount'] for order in orders)
            formatted_customers.append({
                'customer_id': c['customer_id'],
                'username': c['username'],
                'email': c['email'],
                'first_name': c.get('first_name', ''),
                'last_name': c.get('last_name', ''),
                'phone_number': c.get('phone_number', ''),
                'is_active': c.get('is_active', True),
                'created_at': c['created_at'].isoformat() if c.get('created_at') else None,
                'last_login': c['last_login'].isoformat() if c.get('last_login') else None,
                'total_orders': total_orders,
                'total_spent': total_spent
            })

        # Apply status filter
        if status_filter == 'active':
            formatted_customers = [c for c in formatted_customers if c['is_active']]
        elif status_filter == 'inactive':
            formatted_customers = [c for c in formatted_customers if not c['is_active']]

        # Apply search filter
        if search_term:
            formatted_customers = [
                c for c in formatted_customers
                if search_term.lower() in (c['username'] + c['first_name'] + c['last_name'] + c['email']).lower()
            ]

        # Sort
        reverse = (sort_order == 'desc')
        sort_key_map = {
            'id': lambda x: x['customer_id'],
            'username': lambda x: x['username'].lower(),
            'name': lambda x: (x['first_name'] + x['last_name']).lower(),
            'orders': lambda x: x['total_orders'],
            'spent': lambda x: x['total_spent'],
            'joined': lambda x: x['created_at'] or ''
        }
        if sort_by in sort_key_map:
            formatted_customers.sort(key=sort_key_map[sort_by], reverse=reverse)
        else:
            # default to ID sort
            formatted_customers.sort(key=lambda x: x['customer_id'])

        return render_template(
            'admin/admin_customers.html',
            customers=formatted_customers,
            status=status_filter,
            search=search_term,
            sort_by=sort_by,
            sort_order=sort_order
        )

    except Exception as e:
        flash(f'Failed to load customers: {str(e)}', 'danger')
        return redirect(url_for('admin.get_dashboard'))


@admin_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_customers')
def edit_customer(customer_id):
    """Edit customer"""
    customer_model = Customer()

    if request.method == 'GET':
        try:
            customer = customer_model.get_by_id(customer_id)
            if not customer:
                flash('Customer not found', 'danger')
                return redirect(url_for('admin.get_customers_admin'))

            # Get customer orders
            success, customer_orders = OrderService.get_order_list_by_customer_id(customer_id)
            if not success:
                customer_orders = []

            return render_template(
                'admin/admin_customer_form.html',
                customer=customer,
                customer_orders=customer_orders,
                action='edit'
            )

        except Exception as e:
            flash(f'Failed to load customer: {str(e)}', 'danger')
            return redirect(url_for('admin.get_customers_admin'))

    # POST
    if request.method == 'POST':
        data = request.form.to_dict()
        try:
            success, old_customer = AdminService.update_customer_as_admin(customer_id, data)
            if not success:
                flash('Failed to update customer', 'danger')
            else:
                flash('Customer updated successfully', 'success')

            return redirect(url_for('admin.edit_customer', customer_id=customer_id))

        except Exception as e:
            flash(f'Failed to update customer: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_customer', customer_id=customer_id))
        
        
@admin_bp.route('/customers/<int:customer_id>/toggle', methods=['POST'])
@permission_required('manage_customers')
def toggle_customer_status(customer_id): 
    try:
        success, new_status = AdminService.toggle_customer_status(customer_id)
        if not success:
            flash('Failed to toggle customer status', 'danger')
        else:
            status_text = 'activated' if new_status else 'deactivated'
            flash(f'Customer {status_text} successfully', 'success')

        return redirect(url_for('admin.get_customers_admin'))

    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.get_customers_admin'))
    except Exception as e:
        flash(f'Failed to toggle customer status: {str(e)}', 'danger')
        return redirect(url_for('admin.get_customers_admin'))



@admin_bp.route('/customers/<int:customer_id>', methods=['GET'])
@permission_required('view_customers')
def get_customer_details(customer_id):
    """Get customer details"""
    try:
        customer_data = AdminService.get_customer_details(customer_id)
        return jsonify({'customer': customer_data}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to get customer details: {str(e)}'}), 500
    

@admin_bp.route('/customers/<int:customer_id>/password', methods=['PUT'])
@permission_required('view_customers')
def change_customer_password(customer_id): 
    data = request.get_json()
    new_password = data.get('password')
    
    try:
        AdminService.change_customer_password(
            admin_id=session['admin_id'],
            customer_id=customer_id,
            new_password=new_password
        )
        return jsonify({'message': 'Password changed successfully'}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400 if str(e) == 'Password is required' else 404
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


 
         
# ============================================
# ADMIN USER MANAGEMENT (SUPER ADMIN ONLY)
# ============================================
@admin_bp.route('/admins/<int:admin_id>/profile', methods=['GET'])
@admin_required
def get_admin_profile(admin_id):
    current_admin_id = session.get('admin_id')
    current_role = session.get('admin_role')

    try:
        admin = AdminService.get_admin_profile(
            admin_id=admin_id,
            current_admin_id=current_admin_id,
            current_role=current_role
        )
        return render_template('admin/profile.html', admin=admin)
    
    except PermissionError as e:
        flash(str(e), "error")
        return redirect(url_for('admin.get_admin', admin_id=current_admin_id))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('admin.get_admins'))


@admin_bp.route('/admins', methods=['GET'])
@admin_required
def get_admins():
    if session.get('admin_role') not in ['super_admin', 'admin']:
        flash('Only super admin can access this page', 'error')
        return redirect(url_for('admin.get_dashboard'))

    filters = {
        'role': request.args.get('role', ''),
        'status': request.args.get('status', ''),
        'search': request.args.get('search', '')
    }
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')

    admin_users = AdminService.get_admins_list(filters=filters, sort_by=sort_by, sort_order=sort_order)

    return render_template(
        'admin/admins.html',
        admin_users=admin_users,
        role=filters['role'],
        status=filters['status'],
        search=filters['search'],
        sort_by=sort_by,
        sort_order=sort_order
    )
 
@admin_bp.route('/admins/add', methods=['GET'])
@admin_required
def show_add_admin_form():
    """Display Add Admin form"""
    if session.get('admin_role') != 'super_admin':
        flash("Only Super Admins can access this page", "error")
        return redirect(url_for('admin.get_admins'))

    return render_template('admin/add_admin.html')

@admin_bp.route('/admins/<int:admin_id>', methods=['GET'])
@admin_required
def get_admin(admin_id): 
    if session.get('admin_role') != 'super_admin':
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Only super admin can access this page'}), 403
        flash('Only super admin can access this page', 'error')
        return redirect(url_for('admin.get_dashboard'))

     
    admin_data = AdminService.get_admin_by_id(admin_id)

    if not admin_data:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Admin not found'}), 404
        flash('Admin user not found', 'error')
        return redirect(url_for('admin.get_admins'))

     
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'admin': admin_data})

    return render_template('admin/admin_detail.html', admin=admin_data)


@admin_bp.route('/admins/add', methods=['POST'])
@admin_required
def add_admin_from_form():
    if session.get('admin_role') != 'super_admin':
        flash("Only Super Admins can create new admin users", "error")
        return redirect(url_for('admin.get_admins'))

    form = request.form

    admin_id = AdminService.create_admin(
        username=form.get('username'),
        email=form.get('email'),
        password=form.get('password'),
        first_name=form.get('first_name', ''),
        last_name=form.get('last_name', ''),
        role=form.get('role', 'admin'),
        is_active=True if form.get('is_active') == "on" else False,
        created_by=session['admin_id']
    )

    flash("Admin user created successfully!", "success")
    return redirect(url_for('admin.update_admin', admin_id=admin_id))

@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@admin_required
def update_admin(admin_id):
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can update admin users'}), 403

    data = request.get_json()
    success, message = AdminService.update_admin(admin_id, data, updated_by=session.get('admin_id'))
    if not success:
        return jsonify({'error': message}), 404
    return jsonify({'message': message}), 200

@admin_bp.route('/admins/<int:admin_id>', methods=['POST'])
@admin_required
def update_admin_form(admin_id):
    current_admin_id = session.get('admin_id')
    current_role = session.get('admin_role')

    success, message = AdminService.update_admin_from_form(
        admin_id,
        request.form,
        current_admin_id=current_admin_id,
        current_role=current_role
    )

    flash(message, "success" if success else "error")
    if admin_id == current_admin_id:
        return redirect(url_for('admin.get_admin_profile', admin_id=current_admin_id))
    else:
        return redirect(url_for('admin.get_admin', admin_id=admin_id))

@admin_bp.route('/profile/password', methods=['GET', 'POST', 'PUT'])
@admin_required
def change_admin_password():
    current_admin_id = session.get('admin_id')
    if not current_admin_id:
        flash("You must be logged in to change password.", "error")
        return redirect(url_for('admin.admin_login'))

    admin_model = AdminUser()
    admin = admin_model.get_by_id(current_admin_id)
    if not admin:
        flash("Admin user not found.", "error")
        return redirect(url_for('admin.get_dashboard'))

    if request.method in ['POST', 'PUT']:
        # Get password from form (POST) or JSON (PUT)
        new_password = request.form.get('new_password') or (request.json and request.json.get('password'))
        confirm_password = request.form.get('confirm_password')

        if not new_password or (request.method == 'POST' and new_password != confirm_password):
            flash("Passwords do not match or are empty.", "error")
            return redirect(url_for('admin.change_admin_password'))

        success, message = AdminService.change_password(current_admin_id, new_password)
        flash(message, "success" if success else "error")
        if success:
            return redirect(url_for('admin.get_admin_profile', admin_id=current_admin_id))
        return redirect(url_for('admin.change_admin_password'))

    return render_template('admin/admin_password.html', admin=admin)


 
@admin_bp.route('/admins/<int:admin_id>/deactivate', methods=['PUT'])
@admin_required
def deactivate_admin(admin_id):
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can deactivate admin users'}), 403

    success, message = AdminService.deactivate_admin(admin_id)
    status_code = 200 if success else 400
    return jsonify({'message' if success else 'error': message}), status_code


@admin_bp.route('/admins/<int:admin_id>/activate', methods=['PUT'])
@admin_required
def activate_admin(admin_id): 
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can activate admin users'}), 403

    success, message = AdminService.activate_admin(admin_id)
    status_code = 200 if success else 400
    return jsonify({'message' if success else 'error': message}), status_code


 
@admin_bp.route('/admins/<int:admin_id>/delete', methods=['POST'])
@admin_required
def delete_admin(admin_id):
    if session.get('admin_role') != 'super_admin':
        flash("Only super admins can delete admin users.", "error")
        return redirect(url_for('admin.get_admin', admin_id=admin_id))

    success, message = AdminService.delete_admin(admin_id)
    flash(message, "success" if success else "error")

    return redirect(url_for('admin.get_admins'))
 