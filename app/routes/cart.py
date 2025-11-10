"""
Shopping Cart Routes
Handles shopping cart operations (add, update, remove items)
Updated to use psycopg2-based models
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import uuid

from app.models import (
    ShoppingCart, CartItem, CartItemCustomization,
    Product, Category
)

# Create blueprint
cart_bp = Blueprint('cart', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_or_create_cart():
    """
    Get or create shopping cart for current user/session
    
    Returns:
        dict: Cart data or None
    """
    cart_model = ShoppingCart()
    
    # Check if customer is logged in
    if 'customer_id' in session:
        # Get or create customer cart
        carts = cart_model.get_by_customer(session['customer_id'])
        now = datetime.now()
        
        # Find non-expired cart
        for cart in carts:
            if cart.get('expires_at') and cart['expires_at'] > now:
                return cart
        
        # Create new cart if none found
        cart_id = cart_model.create(
            customer_id=session['customer_id'],
            expires_at=now + timedelta(days=30)
        )
        return cart_model.get_by_id(cart_id)
    else:
        # Guest user - use session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
        
        # Get or create guest cart
        carts = cart_model.get_by_session(session['session_id'])
        now = datetime.now()
        
        # Find non-expired cart
        for cart in carts:
            if cart.get('expires_at') and cart['expires_at'] > now:
                return cart
        
        # Create new cart
        cart_id = cart_model.create(
            session_id=session['session_id'],
            expires_at=now + timedelta(days=30)
        )
        return cart_model.get_by_id(cart_id)


def format_cart_response(cart):
    """Format cart data for JSON response"""
    cart_item_model = CartItem()
    product_model = Product()
    category_model = Category()
    cart_model = ShoppingCart()
    
    cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
    
    items = []
    for cart_item in cart_items:
        product = product_model.get_by_id(cart_item['product_id'])
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
        
        items.append({
            'cart_item_id': cart_item['cart_item_id'],
            'product': {
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'description': product.get('description'),
                'base_price': float(product['base_price']),
                'category_name': category['category_name']
            },
            'quantity': cart_item['quantity'],
            'design_file_url': cart_item.get('design_file_url'),
            'customizations': customizations,
            'line_total': line_total,
            'added_at': cart_item['added_at'].isoformat() if cart_item.get('added_at') else None
        })
    
    return {
        'shopping_cart_id': cart['shopping_cart_id'],
        'items': items,
        'total_items': cart_model.get_total_items(cart['shopping_cart_id']),
        'total_quantity': cart_model.get_total_quantity(cart['shopping_cart_id']),
        'cart_total': cart_model.calculate_total(cart['shopping_cart_id']),
        'expires_at': cart['expires_at'].isoformat() if cart.get('expires_at') else None
    }


# ============================================
# CART ROUTES
# ============================================

@cart_bp.route('/', methods=['GET'])
@cart_bp.route('/view', methods=['GET'])
def view_cart():
    """
    Get current shopping cart
    
    Returns:
        JSON cart data with items
    """
    try:
        cart = get_or_create_cart()
        return jsonify({'cart': format_cart_response(cart)}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get cart: {str(e)}'}), 500


@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    """
    Add item to shopping cart
    
    POST JSON:
        - product_id: int (required)
        - quantity: int (required, min=1)
        - design_file_url: string (optional)
        - customizations: object (optional) - key-value pairs
    
    Returns:
        JSON cart data
    """
    data = request.get_json()
    
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    design_file_url = data.get('design_file_url')
    customizations = data.get('customizations', {})
    
    # Validation
    if not product_id:
        return jsonify({'error': 'product_id is required'}), 400
    
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({'error': 'quantity must be a positive integer'}), 400
    
    try:
        # Verify product exists and is active
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product or not product.get('is_active'):
            return jsonify({'error': 'Product not found or inactive'}), 404
        
        # Get or create cart
        cart = get_or_create_cart()
        
        # Check if product already in cart
        cart_item_model = CartItem()
        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        
        existing_item = None
        for item in cart_items:
            if item['product_id'] == product_id:
                existing_item = item
                break
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + quantity
            cart_item_model.update(existing_item['cart_item_id'], quantity=new_quantity)
            cart_item_id = existing_item['cart_item_id']
        else:
            # Create new cart item
            cart_item_id = cart_item_model.create(
                shopping_cart_id=cart['shopping_cart_id'],
                product_id=product_id,
                quantity=quantity,
                design_file_url=design_file_url
            )
        
        # Add or update customizations
        if customizations:
            customization_model = CartItemCustomization()
            
            # Remove existing customizations
            existing_customizations = customization_model.get_by_cart_item(cart_item_id)
            for cust in existing_customizations:
                customization_model.delete(cust['customization_id'])
            
            # Add new customizations
            for key, value in customizations.items():
                customization_model.create(
                    cart_item_id=cart_item_id,
                    customization_key=key,
                    customization_value=str(value)
                )
        
        # Refresh cart
        cart = get_or_create_cart()
        
        return jsonify({
            'message': 'Item added to cart',
            'cart': format_cart_response(cart)
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to add to cart: {str(e)}'}), 500


@cart_bp.route('/update/<int:cart_item_id>', methods=['PUT'])
def update_cart_item(cart_item_id):
    """
    Update cart item quantity or customizations
    
    PUT JSON:
        - quantity: int (optional, min=1)
        - design_file_url: string (optional)
        - customizations: object (optional)
    
    Returns:
        JSON cart data
    """
    data = request.get_json()
    
    quantity = data.get('quantity')
    design_file_url = data.get('design_file_url')
    customizations = data.get('customizations')
    
    if quantity is not None and (not isinstance(quantity, int) or quantity < 1):
        return jsonify({'error': 'quantity must be a positive integer'}), 400
    
    try:
        # Get cart
        cart = get_or_create_cart()
        
        # Get cart item
        cart_item_model = CartItem()
        cart_item = cart_item_model.get_by_id(cart_item_id)
        
        if not cart_item or cart_item['shopping_cart_id'] != cart['shopping_cart_id']:
            return jsonify({'error': 'Cart item not found'}), 404
        
        # Update cart item
        update_data = {}
        if quantity is not None:
            update_data['quantity'] = quantity
        if design_file_url is not None:
            update_data['design_file_url'] = design_file_url
        
        if update_data:
            cart_item_model.update(cart_item_id, **update_data)
        
        # Update customizations
        if customizations is not None:
            customization_model = CartItemCustomization()
            
            # Remove existing customizations
            existing = customization_model.get_by_cart_item(cart_item_id)
            for cust in existing:
                customization_model.delete(cust['customization_id'])
            
            # Add new customizations
            for key, value in customizations.items():
                customization_model.create(
                    cart_item_id=cart_item_id,
                    customization_key=key,
                    customization_value=str(value)
                )
        
        # Refresh cart
        cart = get_or_create_cart()
        
        return jsonify({
            'message': 'Cart item updated',
            'cart': format_cart_response(cart)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update cart item: {str(e)}'}), 500


@cart_bp.route('/remove/<int:cart_item_id>', methods=['DELETE'])
def remove_cart_item(cart_item_id):
    """
    Remove item from cart
    
    Returns:
        JSON cart data
    """
    try:
        # Get cart
        cart = get_or_create_cart()
        
        # Get and delete cart item
        cart_item_model = CartItem()
        cart_item = cart_item_model.get_by_id(cart_item_id)
        
        if not cart_item or cart_item['shopping_cart_id'] != cart['shopping_cart_id']:
            return jsonify({'error': 'Cart item not found'}), 404
        
        cart_item_model.delete(cart_item_id)
        
        # Refresh cart
        cart = get_or_create_cart()
        
        return jsonify({
            'message': 'Item removed from cart',
            'cart': format_cart_response(cart)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to remove cart item: {str(e)}'}), 500


@cart_bp.route('/clear', methods=['POST'])
def clear_cart():
    """
    Remove all items from cart
    
    Returns:
        JSON success message
    """
    try:
        # Get cart
        cart = get_or_create_cart()
        
        # Delete all cart items
        cart_item_model = CartItem()
        cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
        
        for item in cart_items:
            cart_item_model.delete(item['cart_item_id'])
        
        # Refresh cart
        cart = get_or_create_cart()
        
        return jsonify({
            'message': 'Cart cleared',
            'cart': format_cart_response(cart)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to clear cart: {str(e)}'}), 500


@cart_bp.route('/count', methods=['GET'])
def get_cart_count():
    """
    Get cart item count (for badge display)
    
    Returns:
        JSON with cart counts
    """
    try:
        cart = get_or_create_cart()
        cart_model = ShoppingCart()
        
        return jsonify({
            'total_items': cart_model.get_total_items(cart['shopping_cart_id']),
            'total_quantity': cart_model.get_total_quantity(cart['shopping_cart_id'])
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get cart count: {str(e)}'}), 500


@cart_bp.route('/merge', methods=['POST'])
def merge_guest_cart():
    """
    Merge guest cart into customer cart after login
    
    This should be called automatically after customer login
    
    Returns:
        JSON success message
    """
    # Customer must be logged in
    if 'customer_id' not in session:
        return jsonify({'error': 'Customer login required'}), 401
    
    # Must have a guest session
    if 'session_id' not in session:
        return jsonify({'message': 'No guest cart to merge'}), 200
    
    try:
        cart_model = ShoppingCart()
        cart_item_model = CartItem()
        now = datetime.now()
        
        # Get guest cart
        guest_carts = cart_model.get_by_session(session['session_id'])
        guest_cart = None
        
        for cart in guest_carts:
            if cart.get('expires_at') and cart['expires_at'] > now:
                guest_cart = cart
                break
        
        if not guest_cart:
            return jsonify({'message': 'No guest cart to merge'}), 200
        
        guest_cart_items = cart_item_model.get_by_cart(guest_cart['shopping_cart_id'])
        
        if not guest_cart_items:
            return jsonify({'message': 'No guest cart items to merge'}), 200
        
        # Get or create customer cart
        customer_carts = cart_model.get_by_customer(session['customer_id'])
        customer_cart = None
        
        for cart in customer_carts:
            if cart.get('expires_at') and cart['expires_at'] > now:
                customer_cart = cart
                break
        
        if not customer_cart:
            cart_id = cart_model.create(
                customer_id=session['customer_id'],
                expires_at=now + timedelta(days=30)
            )
            customer_cart = cart_model.get_by_id(cart_id)
        
        # Move items from guest cart to customer cart
        customer_cart_items = cart_item_model.get_by_cart(customer_cart['shopping_cart_id'])
        
        for guest_item in guest_cart_items:
            # Check if product already in customer cart
            existing_item = None
            for customer_item in customer_cart_items:
                if customer_item['product_id'] == guest_item['product_id']:
                    existing_item = customer_item
                    break
            
            if existing_item:
                # Add quantities
                new_quantity = existing_item['quantity'] + guest_item['quantity']
                cart_item_model.update(existing_item['cart_item_id'], quantity=new_quantity)
            else:
                # Create new item in customer cart
                cart_item_model.create(
                    shopping_cart_id=customer_cart['shopping_cart_id'],
                    product_id=guest_item['product_id'],
                    quantity=guest_item['quantity'],
                    design_file_url=guest_item.get('design_file_url')
                )
        
        # Delete guest cart
        cart_model.delete(guest_cart['shopping_cart_id'])
        
        # Clear guest session ID
        session.pop('session_id', None)
        
        return jsonify({
            'message': 'Guest cart merged successfully',
            'cart': format_cart_response(customer_cart)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to merge cart: {str(e)}'}), 500