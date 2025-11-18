"""
app/routes/cart.py
Shopping Cart Routes
Handles shopping cart operations (add, update, remove items)
"""
from flask import Blueprint, request, jsonify, session, render_template, flash, redirect, url_for
from datetime import datetime, timedelta
import uuid

from app.models import (
    ShoppingCart, CartItem, CartItemCustomization,
    Product, Category
)
from app.utils import guest_or_customer, PriceHelper, Validators, ImageHelper 

# Create blueprint
cart_bp = Blueprint('cart', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def ensure_session_id():
    """Ensure guest users have a session_id"""
    if 'customer_id' not in session and 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True
    return session.get('session_id')

def get_or_create_cart(): 
    """Get or create shopping cart for current user/session"""
    cart_model = ShoppingCart()
    
    # Ensure guest has session_id
    if 'customer_id' not in session:
        ensure_session_id()
    
    # Check if customer is logged in
    if 'customer_id' in session:
        customer_id = session['customer_id']
        carts = cart_model.get_by_customer(customer_id)
    elif 'session_id' in session:
        session_id = session['session_id']
        carts = cart_model.get_by_session(session_id)
    else:
        return None
    
    # Find non-expired cart
    now = datetime.now()
    for cart in carts:
        if cart.get('expires_at') and cart['expires_at'] > now:
            return cart
    
    # Create new cart if none found
    if 'customer_id' in session:
        cart_id = cart_model.create(
            customer_id=session['customer_id'],
            expires_at=now + timedelta(days=30)
        )
    else:
        cart_id = cart_model.create(
            session_id=session['session_id'],
            expires_at=now + timedelta(days=30)
        )
    
    return cart_model.get_by_id(cart_id)


def update_cart_count():
    """Update cart count in session"""
    try:
        cart = get_or_create_cart()
        if cart:
            cart_model = ShoppingCart()
            session['cart_count'] = cart_model.get_total_items(cart['shopping_cart_id'])
        else:
            session['cart_count'] = 0
    except:
        session['cart_count'] = 0


def format_cart_response(cart): 
    """Format cart data for display"""
    cart_item_model = CartItem()
    product_model = Product()
    category_model = Category()
    cart_model = ShoppingCart()
    
    cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
    
    items = []
    for cart_item in cart_items:
        product = product_model.get_by_id(cart_item['product_id'])
        if not product:
            continue
            
        category = category_model.get_by_id(product['category_id'])
        
        # Get customizations
        customizations = {}
        if cart_item.get('customizations'):
            customizations = {
                c['customization_key']: c['customization_value']
                for c in cart_item['customizations']
            }
        
        # Calculate line total
        line_total = float(product['base_price']) * cart_item['quantity']
        
        # Get product image using ImageHelper
        product_image_url = ImageHelper.get_product_image_url(
            product['product_id'], 
            product['product_name']
        )
        
        items.append({
            'cart_item_id': cart_item['cart_item_id'],
            'product': {
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'description': product.get('description'),
                'base_price': float(product['base_price']),
                'base_price_formatted': PriceHelper.format_currency(product['base_price']),
                'category_name': category['category_name'] if category else 'Uncategorized',
                'image_url': product_image_url
            },
            'quantity': cart_item['quantity'],
            'design_file_url': cart_item.get('design_file_url'),
            'preview_url': cart_item.get('preview_url'),  # <-- add this
            'customizations': customizations,
            'line_total': line_total,
            'line_total_formatted': PriceHelper.format_currency(line_total),
            'added_at': cart_item['added_at'].isoformat() if cart_item.get('added_at') else None
        })
    
    # Calculate totals
    subtotal = sum(item['line_total'] for item in items)
    tax = PriceHelper.calculate_tax(subtotal, tax_rate=0.13)
    total = PriceHelper.calculate_total(subtotal, tax)
    
    return {
        'shopping_cart_id': cart['shopping_cart_id'],
        'items': items,   
        'total_items': cart_model.get_total_items(cart['shopping_cart_id']),
        'total_quantity': cart_model.get_total_quantity(cart['shopping_cart_id']),
        'subtotal': subtotal,
        'subtotal_formatted': PriceHelper.format_currency(subtotal),
        'tax': tax,
        'tax_formatted': PriceHelper.format_currency(tax),
        'cart_total': total,
        'cart_total_formatted': PriceHelper.format_currency(total),
        'expires_at': cart['expires_at'].isoformat() if cart.get('expires_at') else None
    }


# ============================================
# CART ROUTES
# ============================================

@cart_bp.route('/view', methods=['GET'])
def view_cart(): 
    """View shopping cart"""
    # Ensure guest has session
    if 'customer_id' not in session:
        ensure_session_id()
    
    try:
        cart = get_or_create_cart()
        if not cart:
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({'error': 'Could not create cart'}), 500
            flash('Could not load cart', 'error')
            return redirect(url_for('main.homepage'))
            
        cart_data = format_cart_response(cart)
        
        # Update cart count in session
        session['cart_count'] = cart_data['total_items']
        
        # Check if JSON or HTML
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'cart': cart_data}), 200
        
        return render_template('cart/view.html', cart=cart_data)
            
    except Exception as e:
        if request.accept_mimetypes.accept_json:
            return jsonify({'error': f'Failed to get cart: {str(e)}'}), 500
        flash(f'Failed to get cart: {str(e)}', 'error')
        return redirect(url_for('main.homepage'))


@cart_bp.route('/add', methods=['POST'])
def add_to_cart():  
    if 'customer_id' not in session:
        ensure_session_id()
    
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    design_file_url = data.get('design_file_url')
    customizations = data.get('customizations', {})
    
    if not product_id:
        if request.is_json:
            return jsonify({'error': 'product_id is required'}), 400
        flash('Product ID is required', 'error')
        return redirect(request.referrer or url_for('products.get_products'))
    
    # Validate quantity
    is_valid, message = Validators.validate_quantity(quantity)
    if not is_valid:
        if request.is_json:
            return jsonify({'error': message}), 400
        flash(message, 'error')
        return redirect(request.referrer or url_for('products.get_products'))
    
    try:
        # Verify product exists
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product or not product.get('is_active'):
            if request.is_json:
                return jsonify({'error': 'Product not found or inactive'}), 404
            flash('Product not found or inactive', 'error')
            return redirect(url_for('products.get_products'))
        
        # Get or create cart
        cart = get_or_create_cart()
        if not cart:
            if request.is_json:
                return jsonify({'error': 'Failed to create cart'}), 500
            flash('Failed to create cart', 'error')
            return redirect(request.referrer or url_for('products.get_products'))
        
        cart_item_model = CartItem()
        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        
        # Check if product already in cart
        existing_item = None
        for item in cart_items:
            if item['product_id'] == int(product_id):
                existing_item = item
                break
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + int(quantity)
            cart_item_model.update(existing_item['cart_item_id'], quantity=new_quantity)
            cart_item_id = existing_item['cart_item_id']
        else:
            # Create new cart item
            cart_item_id = cart_item_model.create(
                shopping_cart_id=cart['shopping_cart_id'],
                product_id=int(product_id),
                quantity=int(quantity),
                design_file_url=design_file_url
            )
        
        # Handle customizations
        if customizations:
            customization_model = CartItemCustomization()
            existing_customizations = customization_model.get_by_cart_item(cart_item_id)
            for cust in existing_customizations:
                customization_model.delete(cust['customization_id'])
            
            for key, value in customizations.items():
                customization_model.create(
                    cart_item_id=cart_item_id,
                    customization_key=key,
                    customization_value=str(value)
                )
        
        # Refresh cart and update session count
        cart = get_or_create_cart()
        cart_data = format_cart_response(cart)
        session['cart_count'] = cart_data['total_items']
        
        if request.is_json:
            return jsonify({
                'message': 'Item added to cart',
                'cart': cart_data
            }), 201
        
        flash(f'{product["product_name"]} added to cart!', 'success')
        return redirect(request.referrer or url_for('cart.view_cart'))
            
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to add to cart: {str(e)}'}), 500
        flash(f'Failed to add to cart: {str(e)}', 'error')
        return redirect(request.referrer or url_for('products.get_products'))

@cart_bp.route('/update/<int:cart_item_id>', methods=['POST'])
def update_cart_item(cart_item_id):
    """Update quantity of a cart item"""
    try:
        cart = get_or_create_cart()
        if not cart:
            if request.is_json:
                return jsonify({'error': 'Cart not found'}), 404
            flash('Cart not found', 'error')
            return redirect(url_for('cart.view_cart'))
        
        # Get new quantity (from JSON or form)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        new_quantity = int(data.get('quantity', 1))
        
        # Validate
        is_valid, message = Validators.validate_quantity(new_quantity)
        if not is_valid:
            if request.is_json:
                return jsonify({'error': message}), 400
            flash(message, 'error')
            return redirect(url_for('cart.view_cart'))
        
        cart_item_model = CartItem()
        cart_item = cart_item_model.get_by_id(cart_item_id)
        
        if not cart_item or cart_item['shopping_cart_id'] != cart['shopping_cart_id']:
            if request.is_json:
                return jsonify({'error': 'Cart item not found'}), 404
            flash('Cart item not found', 'error')
            return redirect(url_for('cart.view_cart'))
        
        # Update quantity
        cart_item_model.update(cart_item_id, quantity=new_quantity)
        update_cart_count()
        
        # Recalculate totals
        cart = get_or_create_cart()
        cart_data = format_cart_response(cart)
        
        if request.is_json:
            return jsonify({
                'message': 'Cart item updated',
                'cart': cart_data
            }), 200
        
        flash('Cart updated successfully', 'success')
        return redirect(url_for('cart.view_cart'))
    
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to update cart item: {str(e)}'}), 500
        flash(f'Failed to update cart item: {str(e)}', 'error')
        return redirect(url_for('cart.view_cart'))



@cart_bp.route('/remove/<int:cart_item_id>', methods=['POST', 'DELETE'])
def remove_cart_item(cart_item_id): 
    """Remove item from cart"""
    try:
        cart = get_or_create_cart()
        if not cart:
            if request.is_json:
                return jsonify({'error': 'Cart not found'}), 404
            flash('Cart not found', 'error')
            return redirect(url_for('cart.view_cart'))
            
        cart_item_model = CartItem()
        cart_item = cart_item_model.get_by_id(cart_item_id)
        
        if not cart_item or cart_item['shopping_cart_id'] != cart['shopping_cart_id']:
            if request.is_json:
                return jsonify({'error': 'Cart item not found'}), 404
            flash('Cart item not found', 'error')
            return redirect(url_for('cart.view_cart'))
        
        cart_item_model.delete(cart_item_id)
        
        # Update cart count
        update_cart_count()
        
        if request.is_json:
            cart = get_or_create_cart()
            cart_data = format_cart_response(cart)
            return jsonify({
                'message': 'Item removed from cart',
                'cart': cart_data
            }), 200
        
        flash('Item removed from cart', 'success')
        return redirect(url_for('cart.view_cart'))
            
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to remove cart item: {str(e)}'}), 500
        flash(f'Failed to remove cart item: {str(e)}', 'error')
        return redirect(url_for('cart.view_cart'))


@cart_bp.route('/clear', methods=['POST'])
def clear_cart(): 
    """Clear all items from cart"""
    try:
        cart = get_or_create_cart()
        if not cart:
            if request.is_json:
                return jsonify({'error': 'Cart not found'}), 404
            flash('Cart not found', 'error')
            return redirect(url_for('cart.view_cart'))
            
        cart_item_model = CartItem()
        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        
        for item in cart_items:
            cart_item_model.delete(item['cart_item_id'])
        
        # Update session cart count
        session['cart_count'] = 0
        
        if request.is_json:
            return jsonify({'message': 'Cart cleared'}), 200
        
        flash('Cart cleared', 'success')
        return redirect(url_for('cart.view_cart'))
            
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Failed to clear cart: {str(e)}'}), 500
        flash(f'Failed to clear cart: {str(e)}', 'error')
        return redirect(url_for('cart.view_cart'))


@cart_bp.route('/count', methods=['GET'])
def get_cart_count():
    """Get cart item count (useful for AJAX updates)"""
    try:
        cart = get_or_create_cart()
        if cart:
            cart_model = ShoppingCart()
            count = cart_model.get_total_items(cart['shopping_cart_id'])
            session['cart_count'] = count
            return jsonify({'count': count}), 200
        return jsonify({'count': 0}), 200
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)}), 500