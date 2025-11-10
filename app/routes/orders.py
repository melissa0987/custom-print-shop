"""
Orders Routes
Handles order placement, tracking, and history
Updated to use psycopg2-based models
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import random
import string

from app.models import (
    Order, OrderItem, OrderItemCustomization, OrderStatusHistory,
    ShoppingCart, CartItem, Product, Customer, Category
)

# Create blueprint
orders_bp = Blueprint('orders', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime('%y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=3))
    return f"ORD-{timestamp}{random_suffix}"


def format_order_response(order, include_items=True):
    """Format order data for JSON response"""
    order_data = {
        'order_id': order['order_id'],
        'order_number': order['order_number'],
        'order_status': order['order_status'],
        'total_amount': float(order['total_amount']),
        'shipping_address': order['shipping_address'],
        'contact_phone': order.get('contact_phone'),
        'contact_email': order.get('contact_email'),
        'notes': order.get('notes'),
        'created_at': order['created_at'].isoformat() if order.get('created_at') else None,
        'updated_at': order['updated_at'].isoformat() if order.get('updated_at') else None
    }
    
    # Add customer info if available
    if order.get('customer_id'):
        customer_model = Customer()
        customer = customer_model.get_by_id(order['customer_id'])
        if customer:
            order_data['customer'] = {
                'customer_id': customer['customer_id'],
                'username': customer['username'],
                'email': customer['email'],
                'full_name': customer_model.full_name(customer)
            }
    else:
        order_data['customer'] = 'Guest'
    
    # Add items if requested
    if include_items:
        order_item_model = OrderItem()
        order_items = order_item_model.get_by_order(order['order_id'])
        
        product_model = Product()
        category_model = Category()
        
        items = []
        for order_item in order_items:
            product = product_model.get_by_id(order_item['product_id'])
            category = category_model.get_by_id(product['category_id'])
            
            # Get customizations
            customizations = {}
            if order_item.get('customizations'):
                customizations = {
                    c['customization_key']: c['customization_value']
                    for c in order_item['customizations']
                }
            
            items.append({
                'order_item_id': order_item['order_item_id'],
                'product': {
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'category_name': category['category_name']
                },
                'quantity': order_item['quantity'],
                'unit_price': float(order_item['unit_price']),
                'subtotal': float(order_item['subtotal']),
                'design_file_url': order_item.get('design_file_url'),
                'customizations': customizations
            })
        
        order_data['items'] = items
        order_data['total_items'] = len(items)
    
    return order_data


# ============================================
# ORDER PLACEMENT
# ============================================

@orders_bp.route('/checkout', methods=['POST'])
def checkout():
    """
    Create order from shopping cart
    
    POST JSON:
        - shipping_address: string (required)
        - contact_phone: string (optional)
        - contact_email: string (required for guests)
        - notes: string (optional)
    
    Returns:
        JSON order data
    """
    data = request.get_json()
    
    shipping_address = data.get('shipping_address', '').strip()
    contact_phone = data.get('contact_phone', '').strip()
    contact_email = data.get('contact_email', '').strip()
    notes = data.get('notes', '').strip()
    
    # Validation
    if not shipping_address:
        return jsonify({'error': 'Shipping address is required'}), 400
    
    # For guest checkout, email is required
    if 'customer_id' not in session and not contact_email:
        return jsonify({'error': 'Contact email is required for guest checkout'}), 400
    
    try:
        cart_model = ShoppingCart()
        cart_item_model = CartItem()
        order_model = Order()
        order_item_model = OrderItem()
        order_item_customization_model = OrderItemCustomization()
        order_status_history_model = OrderStatusHistory()
        product_model = Product()
        
        # Get cart
        now = datetime.now()
        cart = None
        
        if 'customer_id' in session:
            carts = cart_model.get_by_customer(session['customer_id'])
            for c in carts:
                if c.get('expires_at') and c['expires_at'] > now:
                    cart = c
                    break
            customer_id = session['customer_id']
            session_id = None
        elif 'session_id' in session:
            carts = cart_model.get_by_session(session['session_id'])
            for c in carts:
                if c.get('expires_at') and c['expires_at'] > now:
                    cart = c
                    break
            customer_id = None
            session_id = session['session_id']
        else:
            return jsonify({'error': 'No cart found'}), 404
        
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        # Get cart items
        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        
        if not cart_items or len(cart_items) == 0:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate total
        total_amount = cart_model.calculate_total(cart['shopping_cart_id'])
        
        # Generate order number
        order_number = generate_order_number()
        
        # Get customer email if logged in
        if customer_id and not contact_email:
            customer_model = Customer()
            customer = customer_model.get_by_id(customer_id)
            contact_email = customer.get('email') if customer else None
        
        # Create order
        order_id = order_model.create(
            order_number=order_number,
            total_amount=total_amount,
            shipping_address=shipping_address,
            customer_id=customer_id,
            session_id=session_id,
            order_status='pending',
            contact_phone=contact_phone or None,
            contact_email=contact_email,
            notes=notes or None
        )
        
        # Create order items from cart items
        for cart_item in cart_items:
            product = product_model.get_by_id(cart_item['product_id'])
            unit_price = float(product['base_price'])
            quantity = cart_item['quantity']
            
            order_item_id = order_item_model.create(
                order_id=order_id,
                product_id=cart_item['product_id'],
                quantity=quantity,
                unit_price=unit_price,
                design_file_url=cart_item.get('design_file_url')
            )
            
            # Copy customizations
            if cart_item.get('customizations'):
                for customization in cart_item['customizations']:
                    order_item_customization_model.create(
                        order_item_id=order_item_id,
                        customization_key=customization['customization_key'],
                        customization_value=customization['customization_value']
                    )
        
        # Create initial status history
        order_status_history_model.create(
            order_id=order_id,
            status='pending',
            notes='Order created'
        )
        
        # Clear cart
        for item in cart_items:
            cart_item_model.delete(item['cart_item_id'])
        
        # Get the created order
        order = order_model.get_by_id(order_id)
        
        return jsonify({
            'message': 'Order placed successfully',
            'order': format_order_response(order)
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to place order: {str(e)}'}), 500


# ============================================
# ORDER RETRIEVAL
# ============================================

@orders_bp.route('/', methods=['GET'])
@orders_bp.route('/list', methods=['GET'])
def get_orders():
    """
    Get customer's order history
    
    Query Parameters:
        - status: string (optional) - filter by status
        - page: int (optional, default=1)
        - per_page: int (optional, default=10)
    
    Returns:
        JSON list of orders
    """
    # Customer must be logged in
    if 'customer_id' not in session:
        return jsonify({'error': 'Customer login required'}), 401
    
    status_filter = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    try:
        order_model = Order()
        order_item_model = OrderItem()
        
        orders = order_model.get_by_customer(session['customer_id'])
        
        # Filter by status
        if status_filter:
            orders = [o for o in orders if o.get('order_status') == status_filter]
        
        # Sort by created_at descending
        orders.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
        
        # Get total count
        total_orders = len(orders)
        
        # Pagination
        offset = (page - 1) * per_page
        orders = orders[offset:offset + per_page]
        
        # Format results
        result = []
        for o in orders:
            order_items = order_item_model.get_by_order(o['order_id'])
            result.append({
                'order_id': o['order_id'],
                'order_number': o['order_number'],
                'order_status': o['order_status'],
                'total_amount': float(o['total_amount']),
                'total_items': len(order_items),
                'created_at': o['created_at'].isoformat() if o.get('created_at') else None,
                'updated_at': o['updated_at'].isoformat() if o.get('updated_at') else None
            })
        
        # Pagination info
        total_pages = (total_orders + per_page - 1) // per_page
        
        return jsonify({
            'orders': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_orders': total_orders,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get orders: {str(e)}'}), 500


@orders_bp.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """
    Get order details by ID
    
    Returns:
        JSON order details with items
    """
    try:
        order_model = Order()
        order = order_model.get_by_id(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check ownership (customer or guest session)
        if 'customer_id' in session:
            if order.get('customer_id') != session['customer_id']:
                return jsonify({'error': 'Access denied'}), 403
        elif 'session_id' in session:
            if order.get('session_id') != session['session_id']:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Authentication required'}), 401
        
        return jsonify({'order': format_order_response(order)}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order: {str(e)}'}), 500


@orders_bp.route('/number/<order_number>', methods=['GET'])
def get_order_by_number(order_number):
    """
    Get order by order number
    
    Returns:
        JSON order details
    """
    try:
        order_model = Order()
        
        # Find order by number
        if 'customer_id' in session:
            orders = order_model.get_by_customer(session['customer_id'])
            order = None
            for o in orders:
                if o.get('order_number') == order_number:
                    order = o
                    break
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            return jsonify({'order': format_order_response(order)}), 200
        else:
            return jsonify({'error': 'Customer login required'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order: {str(e)}'}), 500


# ============================================
# ORDER STATUS
# ============================================

@orders_bp.route('/<int:order_id>/status', methods=['GET'])
def get_order_status(order_id):
    """
    Get order status with history
    
    Returns:
        JSON order status and history
    """
    try:
        order_model = Order()
        order = order_model.get_by_id(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check ownership
        if 'customer_id' in session:
            if order.get('customer_id') != session['customer_id']:
                return jsonify({'error': 'Access denied'}), 403
        elif 'session_id' in session:
            if order.get('session_id') != session['session_id']:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get status history
        order_status_history_model = OrderStatusHistory()
        status_records = order_status_history_model.get_by_order(order_id)
        
        history = []
        for status_record in status_records:
            history.append({
                'status': status_record['status'],
                'changed_at': status_record['changed_at'].isoformat() if status_record.get('changed_at') else None,
                'changed_by': order_status_history_model.get_changed_by_name(status_record),
                'notes': status_record.get('notes')
            })
        
        return jsonify({
            'order_number': order['order_number'],
            'current_status': order['order_status'],
            'status_history': history
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order status: {str(e)}'}), 500


# ============================================
# ORDER CANCELLATION
# ============================================

@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """
    Cancel order (only if pending or processing)
    
    POST JSON:
        - reason: string (optional)
    
    Returns:
        JSON success message
    """
    data = request.get_json() or {}
    reason = data.get('reason', 'Customer requested cancellation')
    
    try:
        order_model = Order()
        order = order_model.get_by_id(order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check ownership
        if 'customer_id' in session:
            if order.get('customer_id') != session['customer_id']:
                return jsonify({'error': 'Access denied'}), 403
        elif 'session_id' in session:
            if order.get('session_id') != session['session_id']:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if order can be cancelled
        if not order_model.can_be_cancelled(order):
            return jsonify({
                'error': f'Order cannot be cancelled (current status: {order["order_status"]})'
            }), 400
        
        # Update order status
        order_model.update_status(order_id, 'cancelled')
        
        # Add status history
        order_status_history_model = OrderStatusHistory()
        order_status_history_model.create(
            order_id=order_id,
            status='cancelled',
            notes=reason
        )
        
        # Get updated order
        order = order_model.get_by_id(order_id)
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': format_order_response(order, include_items=False)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to cancel order: {str(e)}'}), 500


# ============================================
# ORDER STATISTICS
# ============================================

@orders_bp.route('/stats', methods=['GET'])
def get_order_stats():
    """
    Get customer's order statistics
    
    Returns:
        JSON with order counts and totals
    """
    # Customer must be logged in
    if 'customer_id' not in session:
        return jsonify({'error': 'Customer login required'}), 401
    
    try:
        order_model = Order()
        orders = order_model.get_by_customer(session['customer_id'])
        
        stats = {
            'total_orders': len(orders),
            'pending_orders': sum(1 for o in orders if o.get('order_status') == 'pending'),
            'processing_orders': sum(1 for o in orders if o.get('order_status') == 'processing'),
            'completed_orders': sum(1 for o in orders if o.get('order_status') == 'completed'),
            'cancelled_orders': sum(1 for o in orders if o.get('order_status') == 'cancelled'),
            'total_spent': float(sum(
                o.get('total_amount', 0) for o in orders 
                if o.get('order_status') == 'completed'
            ))
        }
        
        return jsonify({'stats': stats}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order stats: {str(e)}'}), 500