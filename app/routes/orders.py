"""
app/routes/orders.py
Orders Routes
Handles order placement, tracking, and history
"""
from flask import Blueprint, json, request, jsonify, session, render_template, flash, redirect, url_for
from datetime import datetime
from app.routes.cart import get_or_create_cart, format_cart_response
import uuid

from app.models import (
    Order, OrderItem, OrderItemCustomization, OrderStatusHistory,
    ShoppingCart, CartItem, Product, Customer, Category
)
from app.utils.helpers import OrderHelper, DateHelper
from app.utils import login_required

# Create blueprint
orders_bp = Blueprint('orders', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================
 
def format_order_response(order, include_items=True): 
    order_data = {
        'order_id': order['order_id'],
        'order_number': order['order_number'],
        'order_status': order['order_status'],
        'total_amount': float(order['total_amount']),
        'shipping_address': order['shipping_address'],
        'contact_phone': order.get('contact_phone'),
        'contact_email': order.get('contact_email'),
        'notes': order.get('notes'),
        'created_at': DateHelper.format_datetime(order.get('created_at')),
        'updated_at': DateHelper.format_datetime(order.get('updated_at'))
    }

    # Add customer info
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
            customizations_raw = order_item.get('customizations', [])
            customizations = {}
            if isinstance(customizations_raw, (list, tuple)):
                customizations = {
                    c['customization_key']: c['customization_value']
                    for c in customizations_raw
                }
            elif isinstance(customizations_raw, dict):
                customizations = customizations_raw
            else:
                customizations = {}

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

        order_data['items'] = items if items else []
        order_data['total_items'] = len(items)

    return order_data


# ============================================
# CHECKOUT PAGE
# ============================================

# CHECKOUT GET
@orders_bp.route('/checkout', methods=['GET'])
def checkout_page():
    """Render checkout page"""
    try:
        # Get cart for current session/user
        cart = get_or_create_cart()
        if not cart:
            flash('No cart found', 'error')
            return redirect(url_for('products.get_products'))

        # Format cart data for template
        cart_data = format_cart_response(cart)

        if not cart_data['items']:
            flash('Your cart is empty', 'error')
            return redirect(url_for('cart.view_cart'))

        return render_template('orders/checkout.html', cart=cart_data)

    except Exception as e:
        flash(f'Failed to load checkout: {str(e)}', 'error')
        return redirect(url_for('cart.view_cart'))


@orders_bp.route('/checkout', methods=['POST'])
def checkout(): 
    data = request.form.to_dict() or request.get_json() or {}
    shipping_address = data.get('shipping_address', '').strip()
    contact_phone = data.get('contact_phone', '').strip()
    contact_email = data.get('contact_email', '').strip()
    notes = data.get('notes', '').strip()

    # ============================
    # INPUT VALIDATION
    # ============================
    if not shipping_address:
        if request.is_json:
            return jsonify({'error': 'Shipping address is required'}), 400
        flash('Shipping address is required', 'error')
        return redirect(url_for('orders.checkout_page'))

    if 'customer_id' not in session and not contact_email:
        if request.is_json:
            return jsonify({'error': 'Contact email is required for guest checkout'}), 400
        flash('Contact email is required for guest checkout', 'error')
        return redirect(url_for('orders.checkout_page'))

    try:
        now = datetime.now()

        # ============================
        # LOAD CART
        # ============================
        cart_model = ShoppingCart()
        cart_item_model = CartItem()
        order_model = Order()
        order_item_model = OrderItem()
        order_item_customization_model = OrderItemCustomization()
        order_status_history_model = OrderStatusHistory()
        product_model = Product()

        cart = None
        customer_id = None
        session_id = None

        if 'customer_id' in session:
            customer_id = session['customer_id']
            carts = cart_model.get_by_customer(customer_id)
            for c in carts:
                if c.get('expires_at') and c['expires_at'] > now:
                    cart = c
                    break
        elif 'session_id' in session:
            session_id = session['session_id']
            carts = cart_model.get_by_session(session_id)
            for c in carts:
                if c.get('expires_at') and c['expires_at'] > now:
                    cart = c
                    break

        if not cart:
            error_msg = 'Cart not found or empty'
            if request.is_json:
                return jsonify({'error': error_msg}), 404
            flash(error_msg, 'error')
            return redirect(url_for('cart.view_cart'))

        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        if not cart_items:
            if request.is_json:
                return jsonify({'error': 'Cart is empty'}), 400
            flash('Cart is empty', 'error')
            return redirect(url_for('cart.view_cart'))

        # ============================
        # CALCULATE TOTAL
        # ============================
        cart_data = format_cart_response(cart)
        total_amount = cart_data['cart_total']

        if customer_id and not contact_email:
            customer_model = Customer()
            customer = customer_model.get_by_id(customer_id)
            contact_email = customer.get('email') if customer else None

        # ============================
        # CREATE ORDER
        # ============================
        order_id = order_model.create(
            order_number=None,  # temporarily None
            total_amount=total_amount,
            shipping_address=shipping_address,
            customer_id=customer_id,
            session_id=session_id,
            order_status='pending',
            contact_phone=contact_phone or None,
            contact_email=contact_email,
            notes=notes or None
        )

        # Generate proper order number and update
        order_number = OrderHelper.generate_order_number(order_id)
        order_model.update(order_id, {'order_number': order_number})

        # ============================
        # CREATE ORDER ITEMS
        # ============================
        for cart_item in cart_items:
            product = product_model.get_by_id(cart_item['product_id'])
            order_item_id = order_item_model.create(
                order_id=order_id,
                product_id=cart_item['product_id'],
                quantity=cart_item['quantity'],
                unit_price=float(product['base_price']),
                design_file_url=cart_item.get('design_file_url')
            )

            for customization in cart_item.get('customizations', []):
                order_item_customization_model.create(
                    order_item_id=order_item_id,
                    customization_key=customization['customization_key'],
                    customization_value=customization['customization_value']
                )

        # ============================
        # CREATE INITIAL ORDER STATUS
        # ============================
        order_status_history_model.create(
            order_id=order_id,
            status='pending',
            notes='Order created'
        )

        # ============================
        # CLEAR CART
        # ============================
        for item in cart_items:
            cart_item_model.delete(item['cart_item_id'])
        session['cart_count'] = 0

        # Fetch the newly created order
        order = order_model.get_by_id(order_id)

        # ============================
        # RETURN RESPONSE OR REDIRECT
        # ============================
        if request.is_json:
            return jsonify({
                'message': 'Order placed successfully',
                'order': format_order_response(order)
            }), 201

        # For regular HTML request, redirect to order list page
        flash('Order placed successfully', 'success')
        return redirect(url_for('orders.get_orders'))

    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to place order: {str(e)}'}), 500
        flash(f'Failed to place order: {str(e)}', 'error')
        return redirect(url_for('orders.checkout_page'))

# ============================================
# ORDER RETRIEVAL
# ============================================

# Get customer's order history
@orders_bp.route('/', methods=['GET'])
@orders_bp.route('/list', methods=['GET'])
@login_required
def get_orders(): 
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
        orders_page = orders[offset:offset + per_page]
        
        # Format results
        result = []
        for o in orders_page:
            order_items = order_item_model.get_by_order(o['order_id'])
            result.append({
                'order_id': o['order_id'],
                'order_number': o['order_number'],
                'order_status': o['order_status'],
                'total_amount': float(o['total_amount']),
                'total_items': len(order_items),
                'created_at': DateHelper.format_datetime(o.get('created_at')),
                'updated_at': DateHelper.format_datetime(o.get('updated_at')),  
            })
        
        # Pagination info
        total_pages = (total_orders + per_page - 1) // per_page
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_orders': total_orders,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        # Get stats
        from app.services.order_service import OrderService
        stats = OrderService.get_customer_order_stats(session['customer_id'])
        
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'orders': result, 'pagination': pagination, 'stats': stats}), 200
        
        return render_template('orders/list.html', orders=result, pagination=pagination, stats=stats)
            
    except Exception as e:
        if request.accept_mimetypes.accept_json:
            return jsonify({'error': f'Failed to get orders: {str(e)}'}), 500
        flash(f'Failed to get orders: {str(e)}', 'error')
        return redirect(url_for('main.homepage'))


# Get order details by ID
@orders_bp.route('/<int:order_id>', methods=['GET'])
def get_order(order_id): 
    try:
         
        from app.services.order_service import OrderService
        
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        
        # Check authentication
        if not customer_id and not session_id:
            if request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to view your order', 'error')
            return redirect(url_for('auth.login'))
        
        # Get order using service
        success, result = OrderService.get_order_by_id(
            order_id=order_id,
            customer_id=customer_id,
            session_id=session_id,
            include_items=True
        )
        
        if not success:
            if request.accept_mimetypes.accept_json:
                return jsonify({'error': result}), 404 if 'not found' in result.lower() else 403
            flash(result, 'error')
            return redirect(url_for('orders.get_orders'))
        
        order_data = result
        
        # Format dates for display
        if order_data.get('created_at'):
            order_data['created_at'] = DateHelper.format_datetime(
                datetime.fromisoformat(order_data['created_at'])
            )
        if order_data.get('updated_at'):
            order_data['updated_at'] = DateHelper.format_datetime(
                datetime.fromisoformat(order_data['updated_at'])
            )
        
        # For JSON requests
        if request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']:
            return jsonify({'order': order_data}), 200 
        
        # For HTML requests
        return render_template("orders/detail.html", order=order_data)
            
    except Exception as e:
        import traceback
        print(f"Error in get_order route: {str(e)}")
        print(traceback.format_exc())
        
        if request.accept_mimetypes.accept_json:
            return jsonify({'error': f'Failed to get order: {str(e)}'}), 500
        flash(f'Failed to get order: {str(e)}', 'error')
        return redirect(url_for('orders.get_orders'))


# Get order by order number
@orders_bp.route('/number/<order_number>', methods=['GET'])
def get_order_by_number(order_number): 
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
            
            return redirect(url_for('orders.get_order', order_id=order['order_id']))
        else:
            return jsonify({'error': 'Customer login required'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order: {str(e)}'}), 500


# ============================================
# ORDER STATUS
# ============================================

# Get order status with history
@orders_bp.route('/<int:order_id>/status', methods=['GET'])
def get_order_status(order_id): 
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
                'changed_at': DateHelper.format_datetime(status_record.get('changed_at')),
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

# Cancel order (only if pending or processing)
@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id): 
    data = request.get_json() or request.form.to_dict() or {}
    reason = data.get('reason', 'Customer requested cancellation')
    
    try:
        order_model = Order()
        order = order_model.get_by_id(order_id)
        
        if not order:
            if request.is_json:
                return jsonify({'error': 'Order not found'}), 404
            flash('Order not found', 'error')
            return redirect(url_for('orders.get_orders'))
        
        # Check ownership
        if 'customer_id' in session:
            if order.get('customer_id') != session['customer_id']:
                if request.is_json:
                    return jsonify({'error': 'Access denied'}), 403
                flash('Access denied', 'error')
                return redirect(url_for('orders.get_orders'))
        elif 'session_id' in session:
            if order.get('session_id') != session['session_id']:
                if request.is_json:
                    return jsonify({'error': 'Access denied'}), 403
                flash('Access denied', 'error')
                return redirect(url_for('main.homepage'))
        else:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if order can be cancelled
        if not order_model.can_be_cancelled(order):
            error_msg = f'Order cannot be cancelled (current status: {order["order_status"]})'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('orders.get_order', order_id=order_id))
        
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
        
        if request.is_json:
            return jsonify({
                'message': 'Order cancelled successfully',
                'order': format_order_response(order, include_items=False)
            }), 200
        
        flash('Order cancelled successfully', 'success')
        return redirect(url_for('orders.get_order', order_id=order_id))
            
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to cancel order: {str(e)}'}), 500
        flash(f'Failed to cancel order: {str(e)}', 'error')
        return redirect(url_for('orders.get_orders'))


# ============================================
# ORDER STATISTICS
# ============================================

# Get customer's order statistics
@orders_bp.route('/stats', methods=['GET'])
@login_required
def get_order_stats(): 
    try:
        order_model = Order()
        orders = order_model.get_by_customer(session['customer_id'])  # ✅ call method
        stats = {
            'total_orders': len(orders),
            'pending_orders': sum(1 for o in orders if o.get('order_status') == 'pending'),
            'processing_orders': sum(1 for o in orders if o.get('order_status') == 'processing'),
            'completed_orders': sum(1 for o in orders if o.get('order_status') == 'completed'),
            'cancelled_orders': sum(1 for o in orders if o.get('order_status') == 'cancelled'),
            'total_spent': float(sum(
                o.get('total_amount', 0) for o in orders if o.get('order_status') == 'completed'
            ))
        }
                
        return jsonify({'stats': stats}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get order stats: {str(e)}'}), 500