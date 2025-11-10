"""
Order Service
Business logic for order management
"""

from datetime import datetime
import random
import string

from app.database import get_db_session
from app.models.__models_init__ import (
    Order, OrderItem, OrderItemCustomization,
    OrderStatusHistory, ShoppingCart, CartItem, Customer
)
from app.utils.validators import Validators
from app.utils.helpers import DateHelper


class OrderService:
    """Service class for order operations"""
    
    @staticmethod
    def create_order_from_cart(customer_id=None, session_id=None,
                               shipping_address=None, contact_phone=None,
                               contact_email=None, notes=None):
        """
        Create order from shopping cart
        
        Args:
            customer_id (int, optional): Customer ID
            session_id (str, optional): Guest session ID
            shipping_address (str): Shipping address
            contact_phone (str, optional): Contact phone
            contact_email (str): Contact email
            notes (str, optional): Order notes
            
        Returns:
            tuple: (success: bool, order_data or error_message)
        """
        # Validate required fields
        if not shipping_address or not shipping_address.strip():
            return False, "Shipping address is required"
        
        # For guest checkout, email is required
        if not customer_id and not contact_email:
            return False, "Contact email is required for guest checkout"
        
        try:
            with get_db_session() as db_session:
                # Get cart
                if customer_id:
                    cart = db_session.query(ShoppingCart).filter(
                        ShoppingCart.customer_id == customer_id,
                        ShoppingCart.expires_at > DateHelper.now()
                    ).first()
                elif session_id:
                    cart = db_session.query(ShoppingCart).filter(
                        ShoppingCart.session_id == session_id,
                        ShoppingCart.expires_at > DateHelper.now()
                    ).first()
                else:
                    return False, "No cart found"
                
                if not cart or cart.get_total_items() == 0:
                    return False, "Cart is empty"
                
                # Calculate total
                total_amount = cart.calculate_total()
                
                # Generate unique order number
                order_number = OrderService._generate_order_number()
                while db_session.query(Order).filter_by(
                    order_number=order_number
                ).first():
                    order_number = OrderService._generate_order_number()
                
                # Get customer email if logged in
                if customer_id and not contact_email:
                    customer = db_session.query(Customer).filter_by(
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
                    shipping_address=shipping_address.strip(),
                    contact_phone=contact_phone.strip() if contact_phone else None,
                    contact_email=contact_email,
                    notes=notes.strip() if notes else None
                )
                db_session.add(order)
                db_session.flush()
                
                # Create order items from cart
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
                
                # Create status history
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
                
                db_session.commit()
                
                # Format order data for response
                order_data = {
                    'order_id': order.order_id,
                    'order_number': order.order_number,
                    'order_status': order.order_status,
                    'total_amount': float(order.total_amount),
                    'shipping_address': order.shipping_address,
                    'contact_phone': order.contact_phone,
                    'contact_email': order.contact_email,
                    'notes': order.notes,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
                
                return True, order_data
                
        except Exception as e:
            return False, f"Failed to create order: {str(e)}"
    
    @staticmethod
    def _generate_order_number():
        """
        Generate unique order number
        
        Returns:
            str: Order number (e.g., "ORD-20250110123")
        """
        timestamp = datetime.now().strftime('%y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"ORD-{timestamp}{random_suffix}"
    
    @staticmethod
    def get_customer_orders(customer_id, page=1, per_page=20, status_filter=None):
        """
        Get orders for a customer
        
        Args:
            customer_id (int): Customer ID
            page (int): Page number
            per_page (int): Items per page
            status_filter (str, optional): Filter by order status
            
        Returns:
            tuple: (orders_list, total_count, total_pages)
        """
        try:
            with get_db_session() as db_session:
                query = db_session.query(Order).filter_by(
                    customer_id=customer_id
                ).order_by(Order.created_at.desc())
                
                # Apply status filter if provided
                if status_filter:
                    query = query.filter_by(order_status=status_filter)
                
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                offset = (page - 1) * per_page
                orders = query.offset(offset).limit(per_page).all()
                
                orders_list = [
                    {
                        'order_id': o.order_id,
                        'order_number': o.order_number,
                        'order_status': o.order_status,
                        'total_amount': float(o.total_amount),
                        'total_items': o.get_total_items(),
                        'created_at': o.created_at.isoformat() if o.created_at else None,
                        'updated_at': o.updated_at.isoformat() if o.updated_at else None
                    }
                    for o in orders
                ]
                
                return orders_list, total_count, total_pages
                
        except Exception as e:
            print(f"Error getting customer orders: {str(e)}")
            return [], 0, 0
    
    @staticmethod
    def get_order_by_id(order_id, customer_id=None, session_id=None, include_items=True):
        """
        Get order by ID with ownership check
        
        Args:
            order_id (int): Order ID
            customer_id (int, optional): Customer ID for ownership check
            session_id (str, optional): Session ID for ownership check
            include_items (bool): Include order items in response
            
        Returns:
            tuple: (success: bool, order_data or error_message)
        """
        try:
            with get_db_session() as db_session:
                order = db_session.query(Order).filter_by(
                    order_id=order_id
                ).first()
                
                if not order:
                    return False, "Order not found"
                
                # Verify ownership
                if customer_id and order.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and order.session_id != session_id:
                    return False, "Access denied"
                
                # Format order data
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
                    for item in order.order_items:
                        customizations = {
                            c.customization_key: c.customization_value
                            for c in item.customizations
                        }
                        items.append({
                            'order_item_id': item.order_item_id,
                            'product': {
                                'product_id': item.product.product_id,
                                'product_name': item.product.product_name,
                                'category_name': item.product.category.category_name
                            },
                            'quantity': item.quantity,
                            'unit_price': float(item.unit_price),
                            'subtotal': float(item.subtotal),
                            'design_file_url': item.design_file_url,
                            'customizations': customizations
                        })
                    order_data['items'] = items
                    order_data['total_items'] = len(items)
                
                return True, order_data
                
        except Exception as e:
            return False, f"Failed to get order: {str(e)}"
    
    @staticmethod
    def get_order_by_number(order_number, customer_id=None, session_id=None):
        """
        Get order by order number
        
        Args:
            order_number (str): Order number
            customer_id (int, optional): Customer ID for ownership check
            session_id (str, optional): Session ID for ownership check
            
        Returns:
            tuple: (success: bool, order_data or error_message)
        """
        try:
            with get_db_session() as db_session:
                order = db_session.query(Order).filter_by(
                    order_number=order_number
                ).first()
                
                if not order:
                    return False, "Order not found"
                
                # Verify ownership
                if customer_id and order.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and order.session_id != session_id:
                    return False, "Access denied"
                
                # Use get_order_by_id to format response
                return OrderService.get_order_by_id(
                    order.order_id,
                    customer_id=customer_id,
                    session_id=session_id
                )
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_order_status(order_id, customer_id=None, session_id=None):
        """
        Get order status with history
        
        Args:
            order_id (int): Order ID
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            tuple: (success: bool, status_data or error_message)
        """
        try:
            with get_db_session() as db_session:
                order = db_session.query(Order).filter_by(
                    order_id=order_id
                ).first()
                
                if not order:
                    return False, "Order not found"
                
                # Verify ownership
                if customer_id and order.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and order.session_id != session_id:
                    return False, "Access denied"
                
                # Get status history
                history = []
                for status_record in order.status_history:
                    history.append({
                        'status': status_record.status,
                        'changed_at': status_record.changed_at.isoformat() if status_record.changed_at else None,
                        'changed_by': status_record.get_changed_by_name(),
                        'notes': status_record.notes
                    })
                
                status_data = {
                    'order_number': order.order_number,
                    'current_status': order.order_status,
                    'status_history': history
                }
                
                return True, status_data
                
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def cancel_order(order_id, customer_id=None, session_id=None, reason=None):
        """
        Cancel an order
        
        Args:
            order_id (int): Order ID
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            reason (str, optional): Cancellation reason
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as db_session:
                order = db_session.query(Order).filter_by(
                    order_id=order_id
                ).first()
                
                if not order:
                    return False, "Order not found"
                
                # Verify ownership
                if customer_id and order.customer_id != customer_id:
                    return False, "Access denied"
                if session_id and order.session_id != session_id:
                    return False, "Access denied"
                
                # Check if can be cancelled
                if not order.can_be_cancelled():
                    return False, f"Order cannot be cancelled (current status: {order.order_status})"
                
                # Update order
                order.order_status = 'cancelled'
                order.updated_at = DateHelper.now()
                
                # Add status history
                status_history = OrderStatusHistory(
                    order_id=order.order_id,
                    status='cancelled',
                    notes=reason or 'Customer requested cancellation'
                )
                db_session.add(status_history)
                
                db_session.commit()
                
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
            with get_db_session() as db_session:
                orders = db_session.query(Order).filter_by(
                    customer_id=customer_id
                ).all()
                
                stats = {
                    'total_orders': len(orders),
                    'pending_orders': sum(1 for o in orders if o.order_status == 'pending'),
                    'processing_orders': sum(1 for o in orders if o.order_status == 'processing'),
                    'completed_orders': sum(1 for o in orders if o.order_status == 'delivered'),
                    'cancelled_orders': sum(1 for o in orders if o.order_status == 'cancelled'),
                    'total_spent': float(sum(
                        o.total_amount for o in orders 
                        if o.order_status not in ['cancelled', 'refunded']
                    ))
                }
                
                return stats
                
        except Exception as e:
            print(f"Error getting order stats: {str(e)}")
            return {
                'total_orders': 0,
                'pending_orders': 0,
                'processing_orders': 0,
                'completed_orders': 0,
                'cancelled_orders': 0,
                'total_spent': 0.0
            }
    
    @staticmethod
    def update_order_status(order_id, new_status, admin_id=None, notes=None):
        """
        Update order status (admin only)
        
        Args:
            order_id (int): Order ID
            new_status (str): New status
            admin_id (int, optional): Admin ID who made the change
            notes (str, optional): Status change notes
            
        Returns:
            tuple: (success: bool, message)
        """
        # Validate status
        if not Validators.validate_order_status(new_status):
            return False, "Invalid order status"
        
        try:
            with get_db_session() as db_session:
                order = db_session.query(Order).filter_by(
                    order_id=order_id
                ).first()
                
                if not order:
                    return False, "Order not found"
                
                old_status = order.order_status
                
                # Update order status
                order.order_status = new_status
                order.updated_at = DateHelper.now()
                
                # Add status history
                status_history = OrderStatusHistory(
                    order_id=order.order_id,
                    status=new_status,
                    changed_by_admin_id=admin_id,
                    notes=notes or f'Status changed from {old_status} to {new_status}'
                )
                db_session.add(status_history)
                
                db_session.commit()
                
                return True, f"Order status updated to {new_status}"
                
        except Exception as e:
            return False, f"Failed to update order status: {str(e)}"