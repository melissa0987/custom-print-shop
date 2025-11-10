"""
Order Service
Business logic for order management
Updated to use psycopg2-based models
"""

from datetime import datetime
import random
import string

from app.models import (
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
            cart_model = ShoppingCart()
            cart_item_model = CartItem()
            order_model = Order()
            order_item_model = OrderItem()
            order_item_customization_model = OrderItemCustomization()
            order_status_history_model = OrderStatusHistory()
            
            # Get cart
            now = DateHelper.now()
            cart = None
            
            if customer_id:
                carts = cart_model.get_by_customer(customer_id)
                for c in carts:
                    if c.get('expires_at') and c['expires_at'] > now:
                        cart = c
                        break
            elif session_id:
                carts = cart_model.get_by_session(session_id)
                for c in carts:
                    if c.get('expires_at') and c['expires_at'] > now:
                        cart = c
                        break
            else:
                return False, "No cart found"
            
            if not cart:
                return False, "Cart not found"
            
            # Get cart items
            cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
            
            if not cart_items or len(cart_items) == 0:
                return False, "Cart is empty"
            
            # Calculate total
            total_amount = cart_model.calculate_total(cart['shopping_cart_id'])
            
            # Generate unique order number
            order_number = OrderService._generate_order_number()
            
            # Ensure unique order number
            while order_model.get_by_id(order_number):  # This won't work as expected
                order_number = OrderService._generate_order_number()
            
            # Get customer email if logged in
            if customer_id and not contact_email:
                customer_model = Customer()
                customer = customer_model.get_by_id(customer_id)
                contact_email = customer.get('email') if customer else None
            
            # Create order
            order_id = order_model.create(
                order_number=order_number,
                total_amount=total_amount,
                shipping_address=shipping_address.strip(),
                customer_id=customer_id,
                session_id=session_id,
                order_status='pending',
                contact_phone=contact_phone.strip() if contact_phone else None,
                contact_email=contact_email,
                notes=notes.strip() if notes else None
            )
            
            # Create order items from cart
            for cart_item in cart_items:
                # Calculate subtotal
                from app.models import Product
                product_model = Product()
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
                            customization_key=customization.get('customization_key'),
                            customization_value=customization.get('customization_value')
                        )
            
            # Create status history
            order_status_history_model.create(
                order_id=order_id,
                status='pending',
                notes='Order created'
            )
            
            # Clear cart
            for item in cart_items:
                cart_item_model.delete(item['cart_item_id'])
            
            # Format order data for response
            order = order_model.get_by_id(order_id)
            order_data = {
                'order_id': order['order_id'],
                'order_number': order['order_number'],
                'order_status': order['order_status'],
                'total_amount': float(order['total_amount']),
                'shipping_address': order['shipping_address'],
                'contact_phone': order.get('contact_phone'),
                'contact_email': order.get('contact_email'),
                'notes': order.get('notes'),
                'created_at': order['created_at'].isoformat() if order.get('created_at') else None
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
            order_model = Order()
            orders = order_model.get_by_customer(customer_id)
            
            # Apply status filter if provided
            if status_filter:
                orders = [o for o in orders if o.get('order_status') == status_filter]
            
            # Sort by created_at descending
            orders.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
            
            total_count = len(orders)
            total_pages = (total_count + per_page - 1) // per_page
            
            # Pagination
            offset = (page - 1) * per_page
            orders = orders[offset:offset + per_page]
            
            # Format results
            orders_list = []
            for o in orders:
                order_item_model = OrderItem()
                order_items = order_item_model.get_by_order(o['order_id'])
                
                orders_list.append({
                    'order_id': o['order_id'],
                    'order_number': o['order_number'],
                    'order_status': o['order_status'],
                    'total_amount': float(o['total_amount']),
                    'total_items': len(order_items),
                    'created_at': o['created_at'].isoformat() if o.get('created_at') else None,
                    'updated_at': o['updated_at'].isoformat() if o.get('updated_at') else None
                })
            
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
            order_model = Order()
            order = order_model.get_by_id(order_id)
            
            if not order:
                return False, "Order not found"
            
            # Verify ownership
            if customer_id and order.get('customer_id') != customer_id:
                return False, "Access denied"
            if session_id and order.get('session_id') != session_id:
                return False, "Access denied"
            
            # Format order data
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
                order_items = order_item_model.get_by_order(order_id)
                
                items = []
                for item in order_items:
                    from app.models import Product, Category
                    product_model = Product()
                    product = product_model.get_by_id(item['product_id'])
                    
                    category_model = Category()
                    category = category_model.get_by_id(product['category_id'])
                    
                    # Get customizations
                    customizations = {}
                    if item.get('customizations'):
                        customizations = {
                            c['customization_key']: c['customization_value']
                            for c in item['customizations']
                        }
                    
                    items.append({
                        'order_item_id': item['order_item_id'],
                        'product': {
                            'product_id': product['product_id'],
                            'product_name': product['product_name'],
                            'category_name': category['category_name']
                        },
                        'quantity': item['quantity'],
                        'unit_price': float(item['unit_price']),
                        'subtotal': float(item['subtotal']),
                        'design_file_url': item.get('design_file_url'),
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
            # Note: You may need to add a get_by_order_number method to Order model
            # For now, we'll need to search through orders
            order_model = Order()
            
            # This is inefficient - consider adding get_by_order_number to Order model
            if customer_id:
                orders = order_model.get_by_customer(customer_id)
                order = None
                for o in orders:
                    if o.get('order_number') == order_number:
                        order = o
                        break
                
                if not order:
                    return False, "Order not found"
                
                return OrderService.get_order_by_id(
                    order['order_id'],
                    customer_id=customer_id,
                    session_id=session_id
                )
            else:
                return False, "Customer ID required"
                
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
            order_model = Order()
            order = order_model.get_by_id(order_id)
            
            if not order:
                return False, "Order not found"
            
            # Verify ownership
            if customer_id and order.get('customer_id') != customer_id:
                return False, "Access denied"
            if session_id and order.get('session_id') != session_id:
                return False, "Access denied"
            
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
            
            status_data = {
                'order_number': order['order_number'],
                'current_status': order['order_status'],
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
            order_model = Order()
            order = order_model.get_by_id(order_id)
            
            if not order:
                return False, "Order not found"
            
            # Verify ownership
            if customer_id and order.get('customer_id') != customer_id:
                return False, "Access denied"
            if session_id and order.get('session_id') != session_id:
                return False, "Access denied"
            
            # Check if can be cancelled
            if not order_model.can_be_cancelled(order):
                return False, f"Order cannot be cancelled (current status: {order['order_status']})"
            
            # Update order
            order_model.update_status(order_id, 'cancelled')
            
            # Add status history
            order_status_history_model = OrderStatusHistory()
            order_status_history_model.create(
                order_id=order_id,
                status='cancelled',
                notes=reason or 'Customer requested cancellation'
            )
            
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
            order_model = Order()
            orders = order_model.get_by_customer(customer_id)
            
            stats = {
                'total_orders': len(orders),
                'pending_orders': sum(1 for o in orders if o.get('order_status') == 'pending'),
                'processing_orders': sum(1 for o in orders if o.get('order_status') == 'processing'),
                'completed_orders': sum(1 for o in orders if o.get('order_status') == 'completed'),
                'cancelled_orders': sum(1 for o in orders if o.get('order_status') == 'cancelled'),
                'total_spent': float(sum(
                    o.get('total_amount', 0) for o in orders 
                    if o.get('order_status') not in ['cancelled', 'refunded']
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
            order_model = Order()
            order = order_model.get_by_id(order_id)
            
            if not order:
                return False, "Order not found"
            
            old_status = order['order_status']
            
            # Update order status
            order_model.update_status(order_id, new_status, updated_by=admin_id)
            
            # Add status history
            order_status_history_model = OrderStatusHistory()
            order_status_history_model.create(
                order_id=order_id,
                status=new_status,
                changed_by=admin_id,
                notes=notes or f'Status changed from {old_status} to {new_status}'
            )
            
            return True, f"Order status updated to {new_status}"
                
        except Exception as e:
            return False, f"Failed to update order status: {str(e)}"