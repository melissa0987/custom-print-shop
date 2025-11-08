"""
Shopping Cart Routes
Handles shopping cart operations (add, update, remove items)
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import uuid

from app.database import get_db_session
from app.models import (
    ShoppingCart, CartItem, CartItemCustomization,
    Product, Customer
)

# Create blueprint
cart_bp = Blueprint('cart', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_or_create_cart(db_session):
    """
    Get or create shopping cart for current user/session
    
    Returns:
        ShoppingCart object
    """
    # Check if customer is logged in
    if 'customer_id' in session:
        # Get or create customer cart
        cart = db_session.query(ShoppingCart).filter(
            ShoppingCart.customer_id == session['customer_id'],
            ShoppingCart.expires_at > datetime.now()
        ).first()
        
        if not cart:
            cart = ShoppingCart(
                customer_id=session['customer_id'],
                expires_at=datetime.now() + timedelta(days=30)
            )
            db_session.add(cart)
            db_session.flush()
    else:
        # Guest user - use session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
        
        # Get or create guest cart
        cart = db_session.query(ShoppingCart).filter(
            ShoppingCart.session_id == session['session_id'],
            ShoppingCart.expires_at > datetime.now()
        ).first()
        
        if not cart:
            cart = ShoppingCart(
                session_id=session['session_id'],
                expires_at=datetime.now() + timedelta(days=30)
            )
            db_session.add(cart)
            db_session.flush()
    
    return cart


def format_cart_response(cart):
    """Format cart data for JSON response"""
    items = []
    for cart_item in cart.cart_items:
        # Get customizations
        customizations = {
            c.customization_key: c.customization_value
            for c in cart_item.customizations
        }
        
        items.append({
            'cart_item_id': cart_item.cart_item_id,
            'product': {
                'product_id': cart_item.product.product_id,
                'product_name': cart_item.product.product_name,
                'description': cart_item.product.description,
                'base_price': float(cart_item.product.base_price),
                'category_name': cart_item.product.category.category_name
            },
            'quantity': cart_item.quantity,
            'design_file_url': cart_item.design_file_url,
            'customizations': customizations,
            'line_total': cart_item.get_line_total(),
            'added_at': cart_item.added_at.isoformat() if cart_item.added_at else None
        })
    
    return {
        'shopping_cart_id': cart.shopping_cart_id,
        'items': items,
        'total_items': cart.get_total_items(),
        'total_quantity': cart.get_total_quantity(),
        'cart_total': cart.calculate_total(),
        'expires_at': cart.expires_at.isoformat() if cart.expires_at else None
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
        with get_db_session() as db_session:
            cart = get_or_create_cart(db_session)
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
        with get_db_session() as db_session:
            # Verify product exists and is active
            product = db_session.query(Product).filter_by(
                product_id=product_id,
                is_active=True
            ).first()
            
            if not product:
                return jsonify({'error': 'Product not found or inactive'}), 404
            
            # Get or create cart
            cart = get_or_create_cart(db_session)
            
            # Check if product already in cart
            existing_item = db_session.query(CartItem).filter_by(
                shopping_cart_id=cart.shopping_cart_id,
                product_id=product_id
            ).first()
            
            if existing_item:
                # Update quantity
                existing_item.quantity += quantity
                existing_item.updated_at = datetime.now()
                cart_item = existing_item
            else:
                # Create new cart item
                cart_item = CartItem(
                    shopping_cart_id=cart.shopping_cart_id,
                    product_id=product_id,
                    quantity=quantity,
                    design_file_url=design_file_url
                )
                db_session.add(cart_item)
                db_session.flush()
            
            # Add or update customizations
            if customizations:
                # Remove existing customizations
                db_session.query(CartItemCustomization).filter_by(
                    cart_item_id=cart_item.cart_item_id
                ).delete()
                
                # Add new customizations
                for key, value in customizations.items():
                    customization = CartItemCustomization(
                        cart_item_id=cart_item.cart_item_id,
                        customization_key=key,
                        customization_value=str(value)
                    )
                    db_session.add(customization)
            
            # Update cart timestamp
            cart.updated_at = datetime.now()
            
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
        with get_db_session() as db_session:
            # Get cart
            cart = get_or_create_cart(db_session)
            
            # Get cart item
            cart_item = db_session.query(CartItem).filter_by(
                cart_item_id=cart_item_id,
                shopping_cart_id=cart.shopping_cart_id
            ).first()
            
            if not cart_item:
                return jsonify({'error': 'Cart item not found'}), 404
            
            # Update quantity
            if quantity is not None:
                cart_item.quantity = quantity
            
            # Update design file URL
            if design_file_url is not None:
                cart_item.design_file_url = design_file_url
            
            # Update customizations
            if customizations is not None:
                # Remove existing customizations
                db_session.query(CartItemCustomization).filter_by(
                    cart_item_id=cart_item_id
                ).delete()
                
                # Add new customizations
                for key, value in customizations.items():
                    customization = CartItemCustomization(
                        cart_item_id=cart_item_id,
                        customization_key=key,
                        customization_value=str(value)
                    )
                    db_session.add(customization)
            
            # Update timestamps
            cart_item.updated_at = datetime.now()
            cart.updated_at = datetime.now()
            
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
        with get_db_session() as db_session:
            # Get cart
            cart = get_or_create_cart(db_session)
            
            # Get and delete cart item
            cart_item = db_session.query(CartItem).filter_by(
                cart_item_id=cart_item_id,
                shopping_cart_id=cart.shopping_cart_id
            ).first()
            
            if not cart_item:
                return jsonify({'error': 'Cart item not found'}), 404
            
            db_session.delete(cart_item)
            
            # Update cart timestamp
            cart.updated_at = datetime.now()
            
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
        with get_db_session() as db_session:
            # Get cart
            cart = get_or_create_cart(db_session)
            
            # Delete all cart items
            db_session.query(CartItem).filter_by(
                shopping_cart_id=cart.shopping_cart_id
            ).delete()
            
            # Update cart timestamp
            cart.updated_at = datetime.now()
            
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
        with get_db_session() as db_session:
            cart = get_or_create_cart(db_session)
            
            return jsonify({
                'total_items': cart.get_total_items(),
                'total_quantity': cart.get_total_quantity()
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
        with get_db_session() as db_session:
            # Get guest cart
            guest_cart = db_session.query(ShoppingCart).filter(
                ShoppingCart.session_id == session['session_id'],
                ShoppingCart.expires_at > datetime.now()
            ).first()
            
            if not guest_cart or guest_cart.get_total_items() == 0:
                return jsonify({'message': 'No guest cart items to merge'}), 200
            
            # Get or create customer cart
            customer_cart = db_session.query(ShoppingCart).filter(
                ShoppingCart.customer_id == session['customer_id'],
                ShoppingCart.expires_at > datetime.now()
            ).first()
            
            if not customer_cart:
                customer_cart = ShoppingCart(
                    customer_id=session['customer_id'],
                    expires_at=datetime.now() + timedelta(days=30)
                )
                db_session.add(customer_cart)
                db_session.flush()
            
            # Move items from guest cart to customer cart
            for guest_item in guest_cart.cart_items:
                # Check if product already in customer cart
                existing_item = db_session.query(CartItem).filter_by(
                    shopping_cart_id=customer_cart.shopping_cart_id,
                    product_id=guest_item.product_id
                ).first()
                
                if existing_item:
                    # Add quantities
                    existing_item.quantity += guest_item.quantity
                    existing_item.updated_at = datetime.now()
                else:
                    # Move item to customer cart
                    guest_item.shopping_cart_id = customer_cart.shopping_cart_id
            
            # Delete guest cart
            db_session.delete(guest_cart)
            
            # Update customer cart timestamp
            customer_cart.updated_at = datetime.now()
            
            # Clear guest session ID
            session.pop('session_id', None)
            
            return jsonify({
                'message': 'Guest cart merged successfully',
                'cart': format_cart_response(customer_cart)
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to merge cart: {str(e)}'}), 500