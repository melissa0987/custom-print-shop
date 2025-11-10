"""
Orders Routes
Handles order placement, tracking, and history
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import random
import string

from app.database import get_db_session
from app.models.__models_init__ import (
    Order, OrderItem, OrderItemCustomization, OrderStatusHistory,
    ShoppingCart, CartItem, Product, Customer
)

# Create blueprint
orders_bp = Blueprint('orders', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_order_number():
    """Generate unique order number"""
    # Format: ORD-XXXXX (5 digits)
    timestamp = datetime.now().strftime('%y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=3))
    return f"ORD-{timestamp}{random_suffix}"


def format_order_response(order, include_items=True):
    """Format order data for JSON response"""
    order_data = {
        'order_id': order.order_id,
        'order_number': order.order_number,
        'order_status': order.order_status,
        'total_amount': float(order.total_amount),
        'shipping_address': order.shipping_address,
        'contact_phone': order.contact_phone,
        'contact_email': order.contact_email,
        'notes': order.notes,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'updated_at': order.updated_at.isoformat() if order.updated_at else None
    }
    
    # Add customer info if available
    if order.customer:
        order_data['customer'] = {
            'customer_id': order.customer.customer_id,
            'username': order.customer.username,
            'email': order.customer.email,
            'full_name': order.customer.full_name
        }
    else:
        order_data['customer'] = 'Guest'
    
    # Add items if requested
    if include_items:
        items = []
        for order_item in order.order_items:
            customizations = {
                c.customization_key: c.customization_value
                for c in order_item.customizations
            }
            
            items.append({
                'order_item_id': order_item.order_item_id,
                'product': {
                    'product_id': order_item.product.product_id,
                    'product_name': order_item.product.product_name,
                    'category_name': order_item.product.category.category_name
                },
                'quantity': order_item.quantity,
                'unit_price': float(order_item.unit_price),
                'subtotal': float(order_item.subtotal),
                'design_file_url': order_item.design_file_url,
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
        with get_db_session() as db_session:
            # Get cart
            if 'customer_id' in session:
                cart = db_session.query(ShoppingCart).filter(
                    ShoppingCart.customer_id == session['customer_id'],
                    ShoppingCart.expires_at > datetime.now()
                ).first()
                customer_id = session['customer_id']
                session_id = None
            elif 'session_id' in session:
                cart = db_session.query(ShoppingCart).filter(
                    ShoppingCart.session_id == session['session_id'],
                    ShoppingCart.expires_at > datetime.now()
                ).first()
                customer_id = None
                session_id = session['session_id']
            else:
                return jsonify({'error': 'No cart found'}), 404
            
            if not cart or cart.get_total_items() == 0:
                return jsonify({'error': 'Cart is empty'}), 400
            
            # Calculate total
            total_amount = cart.calculate_total()
            
            # Generate order number
            order_number = generate_order_number()
            
            # Ensure unique order number
            while db_session.query(Order).filter_by(order_number=order_number).first():
                order_number = generate_order_number()
            
            # Get customer email if logged in
            if customer_id:
                customer = db_session.query(Customer).filter_by(customer_id=customer_id).first()
                if not contact_email:
                    contact_email = customer.email
            
            # Create order
            order = Order(
                customer_id=customer_id,
                session_id=session_id,
                order_number=order_number,
                order_status='pending',
                total_amount=total_amount,
                shipping_address=shipping_address,
                contact_phone=contact_phone or None,
                contact_email=contact_email,
                notes=notes or None
            )
            db_session.add(order)
            db_session.flush()
            
            # Create order items from cart items
            for cart_item in cart.cart_items:
                order_item = OrderItem(
                    order_id=order.order_id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.product.base_price,
                    subtotal=cart_item.get_line_total(),
                    design_file_url=cart_item.design_file_url
                )
                db_session.add(order_item)
                db_session.flush()
                
                # Copy customizations
                for customization in cart_item.customizations:
                    order_customization = OrderItemCustomization(
                        order_item_id=order_item.order_item_id,
                        customization_key=customization.customization_key,
                        customization_value=customization.customization_value
                    )
                    db_session.add(order_customization)
            
            # Create initial status history
            status_history = OrderStatusHistory(
                order_id=order.order_id,
                status='pending',
                notes='Order created'
            )
            db_session.add(status_history)
            
            # Clear cart
            db_session.query(CartItem).filter_by(
                shopping_cart_id=cart.shopping_cart_id
            ).delete()
            
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
        with get_db_session() as db_session:
            query = db_session.query(Order).filter_by(
                customer_id=session['customer_id']
            )
            
            # Filter by status
            if status_filter:
                query = query.filter_by(order_status=status_filter)
            
            # Order by date (newest first)
            query = query.order_by(Order.created_at.desc())
            
            # Get total count
            total_orders = query.count()
            
            # Pagination
            offset = (page - 1) * per_page
            orders = query.offset(offset).limit(per_page).all()
            
            # Format results
            result = [format_order_response(order, include_items=False) for order in orders]
            
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
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Check ownership (customer or guest session)
            if 'customer_id' in session:
                if order.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if order.session_id != session['session_id']:
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
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(
                order_number=order_number
            ).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Check ownership
            if 'customer_id' in session:
                if order.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if order.session_id != session['session_id']:
                    return jsonify({'error': 'Access denied'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            return jsonify({'order': format_order_response(order)}), 200
            
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
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Check ownership
            if 'customer_id' in session:
                if order.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if order.session_id != session['session_id']:
                    return jsonify({'error': 'Access denied'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Get status history
            history = []
            for status_record in order.status_history:
                history.append({
                    'status': status_record.status,
                    'changed_at': status_record.changed_at.isoformat() if status_record.changed_at else None,
                    'changed_by': status_record.get_changed_by_name(),
                    'notes': status_record.notes
                })
            
            return jsonify({
                'order_number': order.order_number,
                'current_status': order.order_status,
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
        with get_db_session() as db_session:
            order = db_session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Check ownership
            if 'customer_id' in session:
                if order.customer_id != session['customer_id']:
                    return jsonify({'error': 'Access denied'}), 403
            elif 'session_id' in session:
                if order.session_id != session['session_id']:
                    return jsonify({'error': 'Access denied'}), 403
            else:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check if order can be cancelled
            if not order.can_be_cancelled():
                return jsonify({
                    'error': f'Order cannot be cancelled (current status: {order.order_status})'
                }), 400
            
            # Update order status
            order.order_status = 'cancelled'
            order.updated_at = datetime.now()
            
            # Add status history
            status_history = OrderStatusHistory(
                order_id=order.order_id,
                status='cancelled',
                notes=reason
            )
            db_session.add(status_history)
            
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
        with get_db_session() as db_session:
            orders = db_session.query(Order).filter_by(
                customer_id=session['customer_id']
            ).all()
            
            stats = {
                'total_orders': len(orders),
                'pending_orders': sum(1 for o in orders if o.order_status == 'pending'),
                'processing_orders': sum(1 for o in orders if o.order_status == 'processing'),
                'completed_orders': sum(1 for o in orders if o.order_status == 'completed'),
                'cancelled_orders': sum(1 for o in orders if o.order_status == 'cancelled'),
                'total_spent': float(sum(o.total_amount for o in orders if o.order_status == 'completed'))
            }
            
            return jsonify({'stats': stats}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order stats: {str(e)}'}), 500