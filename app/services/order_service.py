"""
Order Service
Business logic for order processing and management
"""

from datetime import datetime
import random
import string

from app.database import get_db_session
from app.models import (
    Order, OrderItem, OrderItemCustomization, OrderStatusHistory,
    ShoppingCart, CartItem, Product, Customer
)


class OrderService:
    """Service class for order operations"""
    
    @staticmethod
    def generate_order_number():
        """
        Generate unique order number
        
        Returns:
            str: Order number
        """
        timestamp = datetime.now().strftime('%y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"ORD-{timestamp}{random_suffix}"
    
    @staticmethod
    def create_order_from_cart(customer_id, session_id, shipping_address, 
                               contact_phone=None, contact_email=None, notes=None):
        """
        Create order from shopping cart
        
        Args:
            customer_id (int or None): Customer ID
            session_id (str or None): Session ID for guest
            shipping_address (str): Shipping address
            contact_phone (str, optional): Contact phone
            contact_email (str, optional): Contact email (required for guests)
            notes (str, optional): Order notes
            
        Returns:
            tuple: (success: bool, order or error_message)
        """
        if not shipping_address:
            return False, "Shipping address is required"
        
        if not customer_id and not contact_email:
            return False, "Contact email is required for guest checkout"
        
        try:
            with get_db_session() as session:
                # Get cart
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
                
                if not cart or cart.get_total_items() == 0:
                    return False, "Cart is empty"
                
                # Calculate total
                total_amount = cart.calculate_total()
                
                # Generate order number
                order_number = OrderService.generate_order_number()
                
                # Ensure unique
                while session.query(Order).filter_by(order_number=order_number).first():
                    order_number = OrderService.generate_order_number()
                
                # Get customer email if logged in
                if customer_id and not contact_email:
                    customer = session.query(Customer).filter_by(
                        customer_id=customer_id
                    ).first()
                    contact_email = customer.email if customer else None
                
                # Create order
                order = Order(
                    customer_id=customer_id,
                    session_id=session_id,
                    order_number=order_number,
                    order_status='pending',
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    notes=notes
                )
                session.add(order)
                session.flush()
                
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
                    session.add(order_item)
                    session.flush()
                    
                    # Copy customizations
                    for customization in cart_item.customizations:
                        order_customization = OrderItemCustomization(
                            order_item_id=order_item.order_item_id,
                            customization_key=customization.customization_key,
                            customization_value=customization.customization_value
                        )
                        session.add(order_customization)
                
                # Create initial status history
                status_history = OrderStatusHistory(
                    order_id=order.order_id,
                    status='pending',
                    notes='Order created'
                )
                session.add(status_history)
                
                # Clear cart
                session.query(CartItem).filter_by(
                    shopping_cart_id=cart.shopping_cart_id
                ).delete()
                
                return True, order
                
        except Exception as e:
            return False, f"Failed to create order: {str(e)}"
    
    @staticmethod
    def get_order_by_id(order_id):
        """
        Get order by ID
        
        Args:
            order_id (int): Order ID
            
        Returns:
            Order or None
        """
        try:
            with get_db_session() as session:
                return session.query(Order).filter_by(order_id=order_id).first()
        except Exception:
            return None
    
    @staticmethod
    def get_order_by_number(order_number):
        """
        Get order by order number
        
        Args:
            order_number (str): Order number
            
        Returns:
            Order or None
        """
        try:
            with get_db_session() as session:
                return session.query(Order).filter_by(
                    order_number=order_number
                ).first()
        except Exception:
            return None
    
    @staticmethod
    def get_customer_orders(customer_id, status=None, page=1, per_page=10):
        """
        Get customer's orders
        
        Args:
            customer_id (int): Customer ID
            status (str, optional): Filter by status
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (orders, total_count, total_pages)
        """
        try:
            with get_db_session() as session:
                query = session.query(Order).filter_by(customer_id=customer_id)
                
                if status:
                    query = query.filter_by(order_status=status)
                
                query = query.order_by(Order.created_at.desc())
                
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                offset = (page - 1) * per_page
                orders = query.offset(offset).limit(per_page).all()
                
                return orders, total_count, total_pages
                
        except Exception:
            return [], 0, 0
    
    @staticmethod
    def get_order_status_history(order_id):
        """
        Get order status history
        
        Args:
            order_id (int): Order ID
            
        Returns:
            list: List of status history records
        """
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                if not order:
                    return []
                return order.status_history
        except Exception:
            return []
    
    @staticmethod
    def cancel_order(order_id, reason="Customer requested cancellation"):
        """
        Cancel order
        
        Args:
            order_id (int): Order ID
            reason (str): Cancellation reason
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                
                if not order:
                    return False, "Order not found"
                
                if not order.can_be_cancelled():
                    return False, f"Order cannot be cancelled (status: {order.order_status})"
                
                # Update status
                order.order_status = 'cancelled'
                order.updated_at = datetime.now()
                
                # Add status history
                status_history = OrderStatusHistory(
                    order_id=order_id,
                    status='cancelled',
                    notes=reason
                )
                session.add(status_history)
                
                return True, "Order cancelled successfully"
                
        except Exception as e:
            return False, f"Failed to cancel order: {str(e)}"
    
    @staticmethod
    def get_customer_order_stats(customer_id):
        """
        Get customer's order statistics
        
        Args:
            customer_id (int): Customer ID
            
        Returns:
            dict: Order statistics
        """
        try:
            with get_db_session() as session:
                orders = session.query(Order).filter_by(
                    customer_id=customer_id
                ).all()
                
                return {
                    'total_orders': len(orders),
                    'pending_orders': sum(1 for o in orders if o.order_status == 'pending'),
                    'processing_orders': sum(1 for o in orders if o.order_status == 'processing'),
                    'completed_orders': sum(1 for o in orders if o.order_status == 'completed'),
                    'cancelled_orders': sum(1 for o in orders if o.order_status == 'cancelled'),
                    'total_spent': float(sum(o.total_amount for o in orders if o.order_status == 'completed'))
                }
        except Exception:
            return {
                'total_orders': 0,
                'pending_orders': 0,
                'processing_orders': 0,
                'completed_orders': 0,
                'cancelled_orders': 0,
                'total_spent': 0.0
            }
    
    @staticmethod
    def verify_order_ownership(order_id, customer_id=None, session_id=None):
        """
        Verify order ownership
        
        Args:
            order_id (int): Order ID
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            bool: True if user owns the order
        """
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                
                if not order:
                    return False
                
                if customer_id and order.customer_id == customer_id:
                    return True
                if session_id and order.session_id == session_id:
                    return True
                
                return False
        except Exception:
            return False
    
    @staticmethod
    def get_order_items_with_customizations(order_id):
        """
        Get order items with their customizations
        
        Args:
            order_id (int): Order ID
            
        Returns:
            list: List of dicts with item and customization data
        """
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                
                if not order:
                    return []
                
                items = []
                for order_item in order.order_items:
                    customizations = {
                        c.customization_key: c.customization_value
                        for c in order_item.customizations
                    }
                    
                    items.append({
                        'order_item_id': order_item.order_item_id,
                        'product_id': order_item.product_id,
                        'product_name': order_item.product.product_name,
                        'quantity': order_item.quantity,
                        'unit_price': float(order_item.unit_price),
                        'subtotal': float(order_item.subtotal),
                        'design_file_url': order_item.design_file_url,
                        'customizations': customizations
                    })
                
                return items
        except Exception:
            return []
    
    @staticmethod
    def calculate_order_total(order_id):
        """
        Calculate order total from items
        
        Args:
            order_id (int): Order ID
            
        Returns:
            float: Total amount
        """
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                if not order:
                    return 0.0
                return order.calculate_total()
        except Exception:
            return 0.0