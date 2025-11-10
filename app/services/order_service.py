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

# Utilities from your helpers and validators
from app.utils.helpers import DateHelper, OrderHelper, StringHelper
from app.utils.validators import Validators


class OrderService:
    """Service class for order operations"""
    
    @staticmethod
    def _generate_order_number():
        """
        Generate unique order number
        
        Returns:
            str: Order number
        """
        timestamp = datetime.now().strftime('%y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"ORD-{timestamp}{random_suffix}"

    # Public wrapper (kept for backwards compatibility).
    @staticmethod
    def generate_order_number():
        return OrderService._generate_order_number()

    # Create order from shopping cart
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
        # Basic validation & sanitization
        shipping_address = StringHelper.clean_whitespace(shipping_address)
        notes = StringHelper.clean_whitespace(notes) if notes else None

        if not shipping_address:
            return False, "Shipping address is required"

        # If guest checkout, require valid email
        if not customer_id:
            if not contact_email or not Validators.validate_email(contact_email):
                return False, "A valid contact email is required for guest checkout"
        else:
            # If logged in and no contact_email provided, we'll try to fetch from customer record later
            if contact_email and not Validators.validate_email(contact_email):
                contact_email = None

        # Validate phone if provided
        if contact_phone and not Validators.validate_phone_number(contact_phone):
            return False, "Invalid contact phone format"

        try:
            with get_db_session() as session:
                # Get cart (prefer active cart by expiry)
                now = datetime.now()
                if customer_id:
                    cart = session.query(ShoppingCart).filter(
                        ShoppingCart.customer_id == customer_id,
                        ShoppingCart.expires_at > now
                    ).first()
                else:
                    cart = session.query(ShoppingCart).filter(
                        ShoppingCart.session_id == session_id,
                        ShoppingCart.expires_at > now
                    ).first()

                if not cart:
                    return False, "Cart not found or expired"

                # Determine total items (support method or attribute)
                total_items = 0
                try:
                    total_items = cart.get_total_items()
                except Exception:
                    total_items = len(getattr(cart, "cart_items", []) or [])

                if total_items == 0:
                    return False, "Cart is empty"

                # Calculate total amount (rely on cart.calculate_total if available)
                try:
                    total_amount = float(cart.calculate_total())
                except Exception:
                    # Fallback: sum line totals
                    total_amount = 0.0
                    for ci in getattr(cart, "cart_items", []) or []:
                        try:
                            total_amount += float(ci.get_line_total())
                        except Exception:
                            # best-effort compute
                            price = getattr(ci, "unit_price", None) or getattr(getattr(ci, "product", None), "base_price", 0)
                            qty = getattr(ci, "quantity", 0) or 0
                            try:
                                total_amount += float(price) * int(qty)
                            except Exception:
                                pass

                # Generate unique order number (ensure uniqueness)
                order_number = OrderService._generate_order_number()
                while session.query(Order).filter_by(order_number=order_number).first():
                    order_number = OrderService._generate_order_number()

                # If customer is logged in and email not provided, pull from customer record
                if customer_id and not contact_email:
                    customer = session.query(Customer).filter_by(customer_id=customer_id).first()
                    contact_email = getattr(customer, "email", None)

                # Create order record
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
                session.flush()  # ensure order.order_id is available

                # Create order items from cart items
                for cart_item in getattr(cart, "cart_items", []) or []:
                    # Resolve unit price (prefer explicit unit_price on cart_item, otherwise product.base_price)
                    unit_price = getattr(cart_item, "unit_price", None)
                    if unit_price is None:
                        unit_price = getattr(getattr(cart_item, "product", None), "base_price", 0.0)

                    try:
                        subtotal = float(getattr(cart_item, "get_line_total")() if hasattr(cart_item, "get_line_total") else (float(unit_price) * int(getattr(cart_item, "quantity", 0))))
                    except Exception:
                        subtotal = 0.0

                    order_item = OrderItem(
                        order_id=order.order_id,
                        product_id=getattr(cart_item, "product_id", None),
                        quantity=getattr(cart_item, "quantity", 0),
                        unit_price=unit_price,
                        subtotal=subtotal,
                        design_file_url=getattr(cart_item, "design_file_url", None)
                    )
                    session.add(order_item)
                    session.flush()

                    # Copy customizations if present
                    for customization in getattr(cart_item, "customizations", []) or []:
                        order_customization = OrderItemCustomization(
                            order_item_id=order_item.order_item_id,
                            customization_key=getattr(customization, "customization_key", None),
                            customization_value=getattr(customization, "customization_value", None)
                        )
                        session.add(order_customization)

                # Initial status history entry
                status_history = OrderStatusHistory(
                    order_id=order.order_id,
                    status='pending',
                    notes='Order created'
                )
                session.add(status_history)

                # Clear cart items
                try:
                    session.query(CartItem).filter_by(shopping_cart_id=cart.shopping_cart_id).delete()
                except Exception:
                    # best-effort fallback: attempt to clear relationship if present
                    if hasattr(cart, "cart_items"):
                        for ci in list(cart.cart_items):
                            try:
                                session.delete(ci)
                            except Exception:
                                pass

                # Return the created order instance
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
    
    # Get order by order number
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
                # Return history ordered by created_at if available
                try:
                    return sorted(order.status_history, key=lambda h: getattr(h, "created_at", None) or datetime.min, reverse=False)
                except Exception:
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

                # rely on model method can_be_cancelled() if present
                if hasattr(order, "can_be_cancelled"):
                    if not order.can_be_cancelled():
                        return False, f"Order cannot be cancelled (status: {order.order_status})"
                else:
                    # Basic protection: do not cancel if already shipped/delivered/cancelled
                    if order.order_status in ('shipped', 'delivered', 'cancelled', 'refunded'):
                        return False, f"Order cannot be cancelled (status: {order.order_status})"

                order.order_status = 'cancelled'
                order.updated_at = datetime.now()

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
                orders = session.query(Order).filter_by(customer_id=customer_id).all()

                return {
                    'total_orders': len(orders),
                    # map statuses to helpers' expected names - use 'delivered' as completed
                    'pending_orders': sum(1 for o in orders if o.order_status == 'pending'),
                    'processing_orders': sum(1 for o in orders if o.order_status == 'processing'),
                    'completed_orders': sum(1 for o in orders if o.order_status == 'delivered'),
                    'cancelled_orders': sum(1 for o in orders if o.order_status == 'cancelled'),
                    'total_spent': float(sum(o.total_amount for o in orders if o.order_status == 'delivered' and o.total_amount))
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
                for order_item in getattr(order, "order_items", []) or []:
                    customizations = {
                        c.customization_key: c.customization_value
                        for c in getattr(order_item, "customizations", []) or []
                    }

                    items.append({
                        'order_item_id': order_item.order_item_id,
                        'product_id': order_item.product_id,
                        'product_name': getattr(getattr(order_item, "product", None), "product_name", None),
                        'quantity': order_item.quantity,
                        'unit_price': float(order_item.unit_price) if order_item.unit_price is not None else 0.0,
                        'subtotal': float(order_item.subtotal) if order_item.subtotal is not None else 0.0,
                        'design_file_url': getattr(order_item, "design_file_url", None),
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
                # Prefer model's calculate_total method if present
                if hasattr(order, "calculate_total"):
                    return float(order.calculate_total())
                # Fallback: sum item subtotals
                total = 0.0
                for item in getattr(order, "order_items", []) or []:
                    try:
                        total += float(getattr(item, "subtotal", 0.0))
                    except Exception:
                        pass
                return total
        except Exception:
            return 0.0