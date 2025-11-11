""".
app/routes/admin.py
Admin Routes
Handles admin panel operations (orders, products, customers, reports)

"""
# TODO: use render_template for html

from flask import Blueprint, request, jsonify, session 

from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)
from app.utils import admin_required

 
admin_bp = Blueprint('admin', __name__)


# Helper decorator for permissions
# Decorator to require specific admin permission
def permission_required(permission):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                return jsonify({'error': 'Admin authentication required'}), 401
            
            admin_model = AdminUser()
            admin = admin_model.get_by_id(session['admin_id'])
            
            if not admin or not AdminUser.has_permission(admin, permission):
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================
# DASHBOARD
# ============================================
# Get admin dashboard statistics 
@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard(): 
    try:
        order_model = Order()
        customer_model = Customer()
        product_model = Product() 
        
        return jsonify({
            'dashboard': {
                'orders': {
                    'total': 0,
                    'pending': 0,
                    'processing': 0
                },
                'revenue': {
                    'total': 0.0,
                    'month': 0.0
                },
                'customers': {
                    'total': 0,
                    'active': 0
                },
                'products': {
                    'total': len(product_model.get_all()),
                    'active': len(product_model.get_all(active_only=True))
                },
                'recent_orders': []
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard: {str(e)}'}), 500


# ============================================
# ORDER MANAGEMENT
# ============================================

# Get all orders with filtering  
@admin_bp.route('/orders', methods=['GET'])
@permission_required('view_orders')
def get_all_orders():
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        # Note: You need a way to get all orders
        # This is a placeholder implementation
        
        return jsonify({
            'orders': [],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_orders': 0,
                'total_pages': 0
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get orders: {str(e)}'}), 500

 # Get order details 
@admin_bp.route('/orders/<int:order_id>', methods=['GET'])
@permission_required('view_orders')
def get_order_details(order_id):

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

# Update order status 
@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@permission_required('update_order_status')
def update_order_status(order_id):
    
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

#   Get all products 
@admin_bp.route('/products', methods=['GET'])
@permission_required('view_products')
def get_all_products():
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

#  Update product 
@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@permission_required('update_product')
def update_product(product_id):

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


# ============================================
# CUSTOMER MANAGEMENT
# ============================================

# Get all customers 
@admin_bp.route('/customers', methods=['GET'])
@permission_required('view_customers')
def get_all_customers():
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:  
        return jsonify({
            'customers': [],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_customers': 0
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customers: {str(e)}'}), 500


# ============================================
# REPORTS
# ============================================

# Get sales report 
@admin_bp.route('/reports/sales', methods=['GET'])
@permission_required('view_reports')
def get_sales_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')
    
    try: 
        
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

# Get product performance report 
@admin_bp.route('/reports/products', methods=['GET'])
@permission_required('view_reports')
def get_product_report():
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