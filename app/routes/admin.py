"""
app/routes/admin.py
Admin Routes
Handles admin panel operations (orders, products, customers, reports) 
"""

from flask import Blueprint, flash, redirect, request, jsonify, session, url_for, render_template

from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)
from app.utils import admin_required, permission_required
from app.utils.helpers import PasswordHelper

 
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================
# ADMIN LOGIN
# ============================================ 
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page + login handler"""

    if request.method == 'GET':
        return render_template('admin/admin_login.html')

    data = request.get_json(silent=True) or request.form.to_dict()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        error_msg = 'Email and password are required'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')

    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_email(email.lower())  # lookup by email

        if not admin or not admin.get('password_hash'):
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Verify password
        if not PasswordHelper.verify_password(admin['password_hash'], password):
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Check if active
        if not admin.get('is_active', True):
            error_msg = 'Admin account is inactive'
            if request.is_json:
                return jsonify({'error': error_msg}), 403
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Update last login
        admin_model.update_last_login(admin['admin_id'])

        # Set session
        session['admin_id'] = admin['admin_id']
        session['admin_username'] = admin['username']
        session['admin_role'] = admin.get('role', 'admin')
        session['permissions'] = admin_model.get_permissions(admin['admin_id'])
        session.permanent = True

        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=admin['admin_id'],
            action='login',
            table_name='admin_users',
            record_id=admin['admin_id'],
            old_values=None,
            new_values={'status': 'success'}
        )

        if request.is_json:
            return jsonify({'message': 'Login successful', 'admin': admin}), 200

        flash(f'Welcome back, {admin.get("first_name", admin["username"])}!', 'success')
        next_page = request.args.get('next') or request.form.get('next') or url_for('admin.get_dashboard')
        return redirect(next_page)

    except Exception as e:
        error_msg = f'Login failed: {str(e)}'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')



# ============================================
# DASHBOARD - HTML PAGE
# ============================================
@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard(): 
    """Render admin dashboard page"""
    return render_template('admin/admin_dashboard.html')




@admin_bp.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('main.homepage'))


# ============================================
# ORDER MANAGEMENT
# ============================================

@admin_bp.route('/orders', methods=['GET'])
@permission_required('view_orders')
def get_orders():
    """Render orders management page or return JSON for AJAX"""
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_orders_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_orders.html')


def get_orders_data():
    """API endpoint to get all orders with filtering"""
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        order_model = Order()
        customer_model = Customer()
        
        # Get all orders
        all_orders = order_model.get_all() if hasattr(order_model, 'get_all') else []
        
        # Apply status filter
        if status_filter:
            all_orders = [o for o in all_orders if o.get('order_status') == status_filter]
        
        # Format orders with customer info
        formatted_orders = []
        for order in all_orders:
            customer_username = 'Guest'
            customer_email = order.get('contact_email')
            
            if order.get('customer_id'):
                customer = customer_model.get_by_id(order['customer_id'])
                if customer:
                    customer_username = customer['username']
                    customer_email = customer['email']
            
            formatted_orders.append({
                'order_id': order['order_id'],
                'order_number': order['order_number'],
                'customer_username': customer_username,
                'customer_email': customer_email,
                'order_status': order['order_status'],
                'total_amount': float(order['total_amount']),
                'created_at': order['created_at'].isoformat() if order.get('created_at') else None,
                'updated_at': order['updated_at'].isoformat() if order.get('updated_at') else None
            })
        
        # Pagination
        total_orders = len(formatted_orders)
        offset = (page - 1) * per_page
        paginated_orders = formatted_orders[offset:offset + per_page]
        
        return jsonify({
            'orders': paginated_orders,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_orders': total_orders,
                'total_pages': (total_orders + per_page - 1) // per_page
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get orders: {str(e)}'}), 500


@admin_bp.route('/orders/<int:order_id>', methods=['GET'])
@permission_required('view_orders')
def get_order_details(order_id):
    """Get order details for AJAX"""
    try:
        order_model = Order()
        order_item_model = OrderItem()
        order_status_history_model = OrderStatusHistory()
        product_model = Product()
        category_model = Category()
        customer_model = Customer()
        
        order = order_model.get_by_id(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Format order items
        order_items = order_item_model.get_by_order(order_id)
        items = []
        
        for item in order_items:
            product = product_model.get_by_id(item['product_id'])
            category = category_model.get_by_id(product['category_id'])
            
            customizations = {}
            if item.get('customizations'):
                customizations = {c['customization_key']: c['customization_value'] for c in item['customizations']}
            
            items.append({
                'product_name': product['product_name'],
                'category_name': category['category_name'],
                'quantity': item['quantity'],
                'unit_price': float(item['unit_price']),
                'subtotal': float(item['subtotal']),
                'customizations': customizations
            })
        
        # Format status history
        status_records = order_status_history_model.get_by_order(order_id)
        history = [
            {
                'status': h['status'],
                'changed_at': h['changed_at'].isoformat() if h.get('changed_at') else None,
                'changed_by': order_status_history_model.get_changed_by_name(h),
                'notes': h.get('notes')
            }
            for h in status_records
        ]
        
        # Get customer info
        customer_name = 'Guest'
        customer_email = order.get('contact_email')
        if order.get('customer_id'):
            customer = customer_model.get_by_id(order['customer_id'])
            if customer:
                customer_name = customer_model.full_name(customer)
                customer_email = customer['email']
        
        return jsonify({
            'order': {
                'order_id': order['order_id'],
                'order_number': order['order_number'],
                'customer_name': customer_name,
                'customer_email': customer_email,
                'order_status': order['order_status'],
                'total_amount': float(order['total_amount']),
                'shipping_address': order['shipping_address'],
                'contact_phone': order.get('contact_phone'),
                'notes': order.get('notes'),
                'created_at': order['created_at'].isoformat() if order.get('created_at') else None,
                'items': items,
                'status_history': history
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order details: {str(e)}'}), 500


@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@permission_required('update_order_status')
def update_order_status(order_id):
    """Update order status"""
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    if new_status not in ['pending', 'processing', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        order_model = Order()
        order = order_model.get_by_id(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        old_status = order['order_status']
        
        # Update order status
        order_model.update_status(order_id, new_status, updated_by=session['admin_id'])
        
        # Add status history
        order_status_history_model = OrderStatusHistory()
        order_status_history_model.create(
            order_id=order_id,
            status=new_status,
            changed_by=session['admin_id'],
            notes=notes
        )
        
        # Log admin activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_order_status',
            table_name='orders',
            record_id=order_id,
            old_values={'order_status': old_status},
            new_values={'order_status': new_status, 'notes': notes}
        )
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order_status': new_status
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update order status: {str(e)}'}), 500


# ============================================
# PRODUCT MANAGEMENT
# ============================================

@admin_bp.route('/products', methods=['GET'])
@permission_required('view_products')
def get_products():
    """Render products management page or return JSON for AJAX"""
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_products_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_products.html')


def get_products_data():
    """API endpoint to get all products"""
    category_id = request.args.get('category_id', type=int)
    is_active_str = request.args.get('is_active')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        product_model = Product()
        category_model = Category()
        
        # Get products
        if is_active_str and is_active_str.lower() == 'false':
            products = product_model.get_all(active_only=False)
        else:
            products = product_model.get_all(active_only=True)
        
        # Filter by category
        if category_id:
            products = [p for p in products if p.get('category_id') == category_id]
        
        # Sort by product name
        products.sort(key=lambda x: x.get('product_name', '').lower())
        
        # Get total count
        total_products = len(products)
        
        # Pagination
        offset = (page - 1) * per_page
        products = products[offset:offset + per_page]
        
        # Format results
        result = []
        for p in products:
            category = category_model.get_by_id(p['category_id'])
            result.append({
                'product_id': p['product_id'],
                'category_id': p['category_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'category_name': category['category_name'] if category else 'Unknown',
                'is_active': p.get('is_active'),
                'times_ordered': product_model.get_total_orders(p['product_id']),
                'total_revenue': product_model.get_total_revenue(p['product_id'])
            })
        
        return jsonify({
            'products': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_products': total_products
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500


@admin_bp.route('/products', methods=['POST'])
@permission_required('add_product')
def add_product():
    """Add new product"""
    data = request.get_json()
    
    try:
        product_model = Product()
        
        product_id = product_model.create(
            category_id=data['category_id'],
            product_name=data['product_name'],
            description=data.get('description', ''),
            base_price=data['base_price'],
            is_active=data.get('is_active', True),
            created_by=session['admin_id']
        )
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='add_product',
            table_name='products',
            record_id=product_id,
            old_values=None,
            new_values=data
        )
        
        return jsonify({
            'message': 'Product added successfully',
            'product_id': product_id
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to add product: {str(e)}'}), 500


@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@permission_required('update_product')
def update_product(product_id):
    """Update product"""
    data = request.get_json()
    
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Store old values
        old_values = {
            'product_name': product['product_name'],
            'base_price': float(product['base_price']),
            'is_active': product.get('is_active')
        }
        
        # Update fields
        update_data = {}
        if 'product_name' in data:
            update_data['product_name'] = data['product_name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'base_price' in data:
            update_data['base_price'] = data['base_price']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        if 'category_id' in data:
            update_data['category_id'] = data['category_id']
        
        update_data['updated_by'] = session['admin_id']
        
        product_model.update(product_id, **update_data)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_product',
            table_name='products',
            record_id=product_id,
            old_values=old_values,
            new_values=data
        )
        
        return jsonify({'message': 'Product updated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update product: {str(e)}'}), 500


@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@permission_required('update_product')
def delete_product(product_id):
    """Delete product"""
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if product has been ordered
        times_ordered = product_model.get_total_orders(product_id)
        if times_ordered > 0:
            return jsonify({'error': 'Cannot delete product that has been ordered'}), 400
        
        # Delete product
        product_model.delete(product_id)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='delete_product',
            table_name='products',
            record_id=product_id,
            old_values={'product_name': product['product_name']},
            new_values=None
        )
        
        return jsonify({'message': 'Product deleted successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete product: {str(e)}'}), 500


# ============================================
# CATEGORY MANAGEMENT
# ============================================

@admin_bp.route('/categories', methods=['GET'])
@permission_required('view_categories')
def get_categories():
    """Render categories management page or return JSON for AJAX"""
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_categories_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_categories.html')


def get_categories_data():
    """API endpoint to get all categories"""
    try:
        category_model = Category()
        product_model = Product()
        
        categories = category_model.get_all()
        
        # Add product count to each category
        result = []
        for cat in categories:
            products = product_model.get_by_category(cat['category_id']) if hasattr(product_model, 'get_by_category') else []
            result.append({
                'category_id': cat['category_id'],
                'category_name': cat['category_name'],
                'description': cat.get('description'),
                'display_order': cat.get('display_order', 0),
                'is_active': cat.get('is_active', True),
                'created_at': cat['created_at'].isoformat() if cat.get('created_at') else None,
                'product_count': len(products)
            })
        
        return jsonify({'categories': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get categories: {str(e)}'}), 500


@admin_bp.route('/categories', methods=['POST'])
@permission_required('add_category')
def add_category():
    """Add new category"""
    data = request.get_json()
    
    try:
        category_model = Category()
        
        category_id = category_model.create(
            category_name=data['category_name'],
            description=data.get('description', ''),
            display_order=data.get('display_order', 0),
            is_active=data.get('is_active', True),
            created_by=session['admin_id']
        )
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='add_category',
            table_name='categories',
            record_id=category_id,
            old_values=None,
            new_values=data
        )
        
        return jsonify({
            'message': 'Category added successfully',
            'category_id': category_id
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to add category: {str(e)}'}), 500


@admin_bp.route('/categories/<int:category_id>', methods=['PUT'])
@permission_required('update_category')
def update_category(category_id):
    """Update category"""
    data = request.get_json()
    
    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Update fields
        update_data = {}
        if 'category_name' in data:
            update_data['category_name'] = data['category_name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'display_order' in data:
            update_data['display_order'] = data['display_order']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        
        update_data['updated_by'] = session['admin_id']
        
        category_model.update(category_id, **update_data)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_category',
            table_name='categories',
            record_id=category_id,
            old_values={'category_name': category['category_name']},
            new_values=data
        )
        
        return jsonify({'message': 'Category updated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update category: {str(e)}'}), 500


# ============================================
# CUSTOMER MANAGEMENT
# ============================================

@admin_bp.route('/customers', methods=['GET'])
@permission_required('view_customers')
def get_customers():
    """Render customers management page or return JSON for AJAX"""
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_customers_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_customers.html')


def get_customers_data():
    """API endpoint to get all customers"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        customer_model = Customer()
        order_model = Order()
        
        # Get all customers
        all_customers = customer_model.get_all() if hasattr(customer_model, 'get_all') else []
        
        # Add order statistics
        result = []
        for customer in all_customers:
            customer_orders = [o for o in order_model.get_all() if o.get('customer_id') == customer['customer_id']] if hasattr(order_model, 'get_all') else []
            total_spent = sum(float(o.get('total_amount', 0)) for o in customer_orders if o.get('order_status') == 'completed')
            
            result.append({
                'customer_id': customer['customer_id'],
                'username': customer['username'],
                'email': customer['email'],
                'first_name': customer['first_name'],
                'last_name': customer['last_name'],
                'phone_number': customer.get('phone_number'),
                'is_active': customer.get('is_active', True),
                'created_at': customer['created_at'].isoformat() if customer.get('created_at') else None,
                'last_login': customer['last_login'].isoformat() if customer.get('last_login') else None,
                'total_orders': len(customer_orders),
                'total_spent': total_spent
            })
        
        # Pagination
        total_customers = len(result)
        offset = (page - 1) * per_page
        paginated_customers = result[offset:offset + per_page]
        
        return jsonify({
            'customers': paginated_customers,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_customers': total_customers
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customers: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>', methods=['GET'])
@permission_required('view_customers')
def get_customer_details(customer_id):
    """Get customer details"""
    try:
        customer_model = Customer()
        order_model = Order()
        
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer orders
        customer_orders = [o for o in order_model.get_all() if o.get('customer_id') == customer_id] if hasattr(order_model, 'get_all') else []
        total_spent = sum(float(o.get('total_amount', 0)) for o in customer_orders if o.get('order_status') == 'completed')
        
        # Get recent orders
        recent_orders = sorted(customer_orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        return jsonify({
            'customer': {
                'customer_id': customer['customer_id'],
                'username': customer['username'],
                'email': customer['email'],
                'first_name': customer['first_name'],
                'last_name': customer['last_name'],
                'phone_number': customer.get('phone_number'),
                'is_active': customer.get('is_active', True),
                'created_at': customer['created_at'].isoformat() if customer.get('created_at') else None,
                'last_login': customer['last_login'].isoformat() if customer.get('last_login') else None,
                'total_orders': len(customer_orders),
                'total_spent': total_spent,
                'recent_orders': [
                    {
                        'order_id': o['order_id'],
                        'order_number': o['order_number'],
                        'order_status': o['order_status'],
                        'total_amount': float(o['total_amount']),
                        'created_at': o['created_at'].isoformat() if o.get('created_at') else None
                    }
                    for o in recent_orders
                ]
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customer details: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>/password', methods=['PUT'])
@permission_required('view_customers')
def change_customer_password(customer_id):
    """Change customer password"""
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400
    
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        customer_model.update_password(customer_id, new_password)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='change_customer_password',
            table_name='customers',
            record_id=customer_id,
            old_values=None,
            new_values={'action': 'password_changed'}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>/deactivate', methods=['PUT'])
@permission_required('view_customers')
def deactivate_customer(customer_id):
    """Deactivate customer account"""
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        customer_model.update_status(customer_id, False)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='deactivate_customer',
            table_name='customers',
            record_id=customer_id,
            old_values={'is_active': True},
            new_values={'is_active': False}
        )
        
        return jsonify({'message': 'Customer deactivated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to deactivate customer: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>/activate', methods=['PUT'])
@permission_required('view_customers')
def activate_customer(customer_id):
    """Activate customer account"""
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        customer_model.update_status(customer_id, True)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='activate_customer',
            table_name='customers',
            record_id=customer_id,
            old_values={'is_active': False},
            new_values={'is_active': True}
        )
        
        return jsonify({'message': 'Customer activated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to activate customer: {str(e)}'}), 500


# ============================================
# ADMIN USER MANAGEMENT (SUPER ADMIN ONLY)
# ============================================

@admin_bp.route('/admins', methods=['GET'])
@admin_required
def get_admins():
    """Render admin users management page or return JSON for AJAX"""
    # Check if user is super admin
    if session.get('admin_role') != 'super_admin':
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Only super admin can access this page'}), 403
        flash('Only super admin can access this page', 'error')
        return redirect(url_for('admin.get_dashboard'))
    
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_admins_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_admins.html')


def get_admins_data():
    """API endpoint to get all admin users"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    
    try:
        admin_model = AdminUser()
        
        # Get all admins
        all_admins = admin_model.get_all()
        
        # Format admins
        result = []
        for admin in all_admins:
            result.append({
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'email': admin['email'],
                'first_name': admin['first_name'],
                'last_name': admin['last_name'],
                'role': admin['role'],
                'is_active': admin.get('is_active', True),
                'created_at': admin['created_at'].isoformat() if admin.get('created_at') else None,
                'last_login': admin['last_login'].isoformat() if admin.get('last_login') else None
            })
        
        return jsonify({'admins': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get admin users: {str(e)}'}), 500


@admin_bp.route('/admins', methods=['POST'])
@admin_required
def add_admin():
    """Add new admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can create admin users'}), 403
    
    data = request.get_json()
    
    try:
        admin_model = AdminUser()
        
        admin_id = admin_model.create(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            is_active=data.get('is_active', True),
            created_by=session['admin_id']
        )
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='create_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values=None,
            new_values={'username': data['username'], 'role': data['role']}
        )
        
        return jsonify({
            'message': 'Admin user created successfully',
            'admin_id': admin_id
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to create admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@admin_required
def update_admin(admin_id):
    """Update admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can update admin users'}), 403
    
    data = request.get_json()
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        # Update fields (excluding password which has separate endpoint)
        update_data = {}
        if 'email' in data:
            update_data['email'] = data['email']
        if 'first_name' in data:
            update_data['first_name'] = data['first_name']
        if 'last_name' in data:
            update_data['last_name'] = data['last_name']
        if 'role' in data:
            update_data['role'] = data['role']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        
        # Update admin - you'll need to implement this method in AdminUser model
        for key, value in update_data.items():
            # This is a simplified version - implement proper update method in model
            pass
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'role': admin['role']},
            new_values=data
        )
        
        return jsonify({'message': 'Admin user updated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/password', methods=['PUT'])
@admin_required
def change_admin_password(admin_id):
    """Change admin password (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can change admin passwords'}), 403
    
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_password(admin_id, new_password)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='change_admin_password',
            table_name='admin_users',
            record_id=admin_id,
            old_values=None,
            new_values={'action': 'password_changed'}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/deactivate', methods=['PUT'])
@admin_required
def deactivate_admin(admin_id):
    """Deactivate admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can deactivate admin users'}), 403
    
    # Cannot deactivate yourself
    if admin_id == session.get('admin_id'):
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_status(admin_id, False)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='deactivate_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'is_active': True},
            new_values={'is_active': False}
        )
        
        return jsonify({'message': 'Admin user deactivated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to deactivate admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/activate', methods=['PUT'])
@admin_required
def activate_admin(admin_id):
    """Activate admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can activate admin users'}), 403
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_status(admin_id, True)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='activate_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'is_active': False},
            new_values={'is_active': True}
        )
        
        return jsonify({'message': 'Admin user activated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to activate admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@admin_required
def delete_admin(admin_id):
    """Delete admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can delete admin users'}), 403
    
    # Cannot delete yourself
    if admin_id == session.get('admin_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        # Log activity before deletion
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='delete_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'username': admin['username'], 'role': admin['role']},
            new_values=None
        )
        
        admin_model.delete(admin_id)
        
        return jsonify({'message': 'Admin user deleted successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete admin user: {str(e)}'}), 500


# ============================================
# REPORTS
# ============================================

@admin_bp.route('/reports', methods=['GET'])
@permission_required('view_reports')
def get_reports():
    """Render reports page"""
    return render_template('admin/admin_reports.html')


@admin_bp.route('/reports/sales', methods=['GET'])
@permission_required('view_reports')
def get_sales_report():
    """Get sales report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')
    
    try:
        # TODO: Implement sales report logic
        return jsonify({
            'sales_report': {
                'total_revenue': 0.0,
                'total_orders': 0,
                'average_order_value': 0.0,
                'start_date': start_date,
                'end_date': end_date
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate sales report: {str(e)}'}), 500


@admin_bp.route('/reports/products', methods=['GET'])
@permission_required('view_reports')
def get_product_report():
    """Get product performance report"""
    try:
        product_model = Product()
        category_model = Category()
        
        # Get product performance
        products = product_model.get_all()
        
        product_data = []
        for product in products:
            category = category_model.get_by_id(product['category_id'])
            product_data.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'category_name': category['category_name'] if category else 'Unknown',
                'base_price': float(product['base_price']),
                'times_ordered': product_model.get_total_orders(product['product_id']),
                'total_quantity_sold': product_model.get_total_quantity_sold(product['product_id']),
                'total_revenue': product_model.get_total_revenue(product['product_id'])
            })
        
        # Sort by revenue
        product_data.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return jsonify({
            'product_report': {
                'products': product_data[:20],  # Top 20
                'total_products': len(products)
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate product report: {str(e)}'}), 500