"""
Cart Service
Business logic for shopping cart management
"""

from datetime import datetime, timedelta
import uuid

from app.database import get_db_session
from app.models import (
    ShoppingCart, CartItem, CartItemCustomization,
    Product, Customer
)


class CartService:
    """Service class for shopping cart operations"""
    
    @staticmethod
    def get_or_create_cart(customer_id=None, session_id=None):
        """
        Get or create shopping cart
        
        Args:
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID for guest
            
        Returns:
            ShoppingCart or None
        """
        if not customer_id and not session_id:
            return None
        
        try:
            with get_db_session() as session:
                # Find existing cart
                if customer_id:
                    cart = session.query(ShoppingCart).filter(
                        ShoppingCart.customer_id == customer_id,
                        ShoppingCart.expires_at > datetime.now()
                    ).first()
                else:
                    cart = session.query(ShoppingCart).filter(
                        ShoppingCart.session_id == session_id,
                        ShoppingCart.expires_at > datetime.now()
                    ).first()
                
                # Create new cart if not found
                if not cart:
                    cart = ShoppingCart(
                        customer_id=customer_id,
                        session_id=session_id,
                        expires_at=datetime.now() + timedelta(days=30)
                    )
                    session.add(cart)
                    session.flush()
                
                return cart
                
        except Exception as e:
            print(f"Error getting/creating cart: {e}")
            return None
    
    @staticmethod
    def get_cart(shopping_cart_id):
        """
        Get cart by ID
        
        Args:
            shopping_cart_id (int): Shopping cart ID
            
        Returns:
            ShoppingCart or None
        """
        try:
            with get_db_session() as session:
                return session.query(ShoppingCart).filter_by(
                    shopping_cart_id=shopping_cart_id
                ).first()
        except Exception:
            return None
    
    @staticmethod
    def add_to_cart(customer_id, session_id, product_id, quantity, 
                    design_file_url=None, customizations=None):
        """
        Add item to cart
        
        Args:
            customer_id (int or None): Customer ID
            session_id (str or None): Session ID
            product_id (int): Product ID
            quantity (int): Quantity
            design_file_url (str, optional): Design file URL
            customizations (dict, optional): Customization key-value pairs
            
        Returns:
            tuple: (success: bool, cart or error_message)
        """
        if quantity < 1:
            return False, "Quantity must be at least 1"
        
        try:
            with get_db_session() as session:
                # Verify product exists and is active
                product = session.query(Product).filter_by(
                    product_id=product_id,
                    is_active=True
                ).first()
                
                if not product:
                    return False, "Product not found or inactive"
                
                # Get or create cart
                cart = CartService.get_or_create_cart(customer_id, session_id)
                if not cart:
                    return False, "Failed to create cart"
                
                # Check if product already in cart
                existing_item = session.query(CartItem).filter_by(
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
                    session.add(cart_item)
                    session.flush()
                
                # Handle customizations
                if customizations:
                    # Remove existing customizations
                    session.query(CartItemCustomization).filter_by(
                        cart_item_id=cart_item.cart_item_id
                    ).delete()
                    
                    # Add new customizations
                    for key, value in customizations.items():
                        customization = CartItemCustomization(
                            cart_item_id=cart_item.cart_item_id,
                            customization_key=key,
                            customization_value=str(value)
                        )
                        session.add(customization)
                
                # Update cart timestamp
                cart.updated_at = datetime.now()
                
                return True, cart
                
        except Exception as e:
            return False, f"Failed to add to cart: {str(e)}"
    
    @staticmethod
    def update_cart_item(cart_item_id, quantity=None, design_file_url=None, 
                         customizations=None, customer_id=None, session_id=None):
        """
        Update cart item
        
        Args:
            cart_item_id (int): Cart item ID
            quantity (int, optional): New quantity
            design_file_url (str, optional): Design file URL
            customizations (dict, optional): Customizations
            customer_id (int, optional): Customer ID for ownership check
            session_id (str, optional): Session ID for ownership check
            
        Returns:
            tuple: (success: bool, cart or error_message)
        """
        if quantity is not None and quantity < 1:
            return False, "Quantity must be at least 1"
        
        try:
            with get_db_session() as session:
                cart_item = session.query(CartItem).filter_by(
                    cart_item_id=cart_item_id
                ).first()
                
                if not cart_item:
                    return False, "Cart item not found"
                
                # Verify ownership
                cart = cart_item.shopping_cart
                if customer_id and cart.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and cart.session_id != session_id:
                    return False, "Access denied"
                
                # Update fields
                if quantity is not None:
                    cart_item.quantity = quantity
                if design_file_url is not None:
                    cart_item.design_file_url = design_file_url
                
                # Update customizations
                if customizations is not None:
                    session.query(CartItemCustomization).filter_by(
                        cart_item_id=cart_item_id
                    ).delete()
                    
                    for key, value in customizations.items():
                        customization = CartItemCustomization(
                            cart_item_id=cart_item_id,
                            customization_key=key,
                            customization_value=str(value)
                        )
                        session.add(customization)
                
                cart_item.updated_at = datetime.now()
                cart.updated_at = datetime.now()
                
                return True, cart
                
        except Exception as e:
            return False, f"Failed to update cart item: {str(e)}"
    
    @staticmethod
    def remove_from_cart(cart_item_id, customer_id=None, session_id=None):
        """
        Remove item from cart
        
        Args:
            cart_item_id (int): Cart item ID
            customer_id (int, optional): Customer ID for ownership check
            session_id (str, optional): Session ID for ownership check
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                cart_item = session.query(CartItem).filter_by(
                    cart_item_id=cart_item_id
                ).first()
                
                if not cart_item:
                    return False, "Cart item not found"
                
                # Verify ownership
                cart = cart_item.shopping_cart
                if customer_id and cart.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and cart.session_id != session_id:
                    return False, "Access denied"
                
                session.delete(cart_item)
                cart.updated_at = datetime.now()
                
                return True, "Item removed from cart"
                
        except Exception as e:
            return False, f"Failed to remove item: {str(e)}"
    
    @staticmethod
    def clear_cart(customer_id=None, session_id=None):
        """
        Clear all items from cart
        
        Args:
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                # Find cart
                if customer_id:
                    cart = session.query(ShoppingCart).filter_by(
                        customer_id=customer_id
                    ).first()
                else:
                    cart = session.query(ShoppingCart).filter_by(
                        session_id=session_id
                    ).first()
                
                if not cart:
                    return True, "Cart already empty"
                
                # Delete all items
                session.query(CartItem).filter_by(
                    shopping_cart_id=cart.shopping_cart_id
                ).delete()
                
                cart.updated_at = datetime.now()
                
                return True, "Cart cleared"
                
        except Exception as e:
            return False, f"Failed to clear cart: {str(e)}"
    
    @staticmethod
    def merge_guest_cart_to_customer(guest_session_id, customer_id):
        """
        Merge guest cart into customer cart
        
        Args:
            guest_session_id (str): Guest session ID
            customer_id (int): Customer ID
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                # Get guest cart
                guest_cart = session.query(ShoppingCart).filter(
                    ShoppingCart.session_id == guest_session_id,
                    ShoppingCart.expires_at > datetime.now()
                ).first()
                
                if not guest_cart or guest_cart.get_total_items() == 0:
                    return True, "No guest cart to merge"
                
                # Get or create customer cart
                customer_cart = session.query(ShoppingCart).filter(
                    ShoppingCart.customer_id == customer_id,
                    ShoppingCart.expires_at > datetime.now()
                ).first()
                
                if not customer_cart:
                    customer_cart = ShoppingCart(
                        customer_id=customer_id,
                        expires_at=datetime.now() + timedelta(days=30)
                    )
                    session.add(customer_cart)
                    session.flush()
                
                # Move items from guest cart to customer cart
                for guest_item in guest_cart.cart_items:
                    # Check if product already in customer cart
                    existing_item = session.query(CartItem).filter_by(
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
                session.delete(guest_cart)
                customer_cart.updated_at = datetime.now()
                
                return True, "Cart merged successfully"
                
        except Exception as e:
            return False, f"Failed to merge cart: {str(e)}"
    
    @staticmethod
    def calculate_cart_total(shopping_cart_id):
        """
        Calculate cart total
        
        Args:
            shopping_cart_id (int): Shopping cart ID
            
        Returns:
            float: Total amount
        """
        try:
            with get_db_session() as session:
                cart = session.query(ShoppingCart).filter_by(
                    shopping_cart_id=shopping_cart_id
                ).first()
                
                if not cart:
                    return 0.0
                
                return cart.calculate_total()
        except Exception:
            return 0.0
    
    @staticmethod
    def get_cart_count(customer_id=None, session_id=None):
        """
        Get cart item counts
        
        Args:
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            dict: {'total_items': int, 'total_quantity': int}
        """
        try:
            cart = CartService.get_or_create_cart(customer_id, session_id)
            if not cart:
                return {'total_items': 0, 'total_quantity': 0}
            
            return {
                'total_items': cart.get_total_items(),
                'total_quantity': cart.get_total_quantity()
            }
        except Exception:
            return {'total_items': 0, 'total_quantity': 0}
    
    @staticmethod
    def cleanup_expired_carts():
        """
        Remove expired carts (should be run periodically)
        
        Returns:
            int: Number of carts deleted
        """
        try:
            with get_db_session() as session:
                expired_carts = session.query(ShoppingCart).filter(
                    ShoppingCart.expires_at < datetime.now()
                ).all()
                
                count = len(expired_carts)
                
                for cart in expired_carts:
                    session.delete(cart)
                
                return count
        except Exception as e:
            print(f"Error cleaning up carts: {e}")
            return 0