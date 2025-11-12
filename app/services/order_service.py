"""
app/services/order_service.py
Order Service
Business logic for order management

"""

from datetime import datetime
 
import random,  string

from app.database import get_cursor
from app.models import (
    Order, OrderItem, OrderItemCustomization,
    OrderStatusHistory, ShoppingCart, CartItem, Customer, Product, Category, order_item
)
from app.utils.validators import Validators
from app.utils.helpers import DateHelper 


class OrderService: 
    
    # Create order from shopping cart
    @staticmethod
    def create_order_from_cart(customer_id=None, session_id=None, shipping_address=None, contact_phone=None, contact_email=None, notes=None): 
        
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
            
            ## Ensure unique order number
            max_attempts = 10
            attempts = 0
            while attempts < max_attempts:
                if not order_model.get_by_order_number(order_number):
                    break
                order_number = OrderService._generate_order_number()
                attempts += 1

            if attempts >= max_attempts:
                return False, "Failed to generate unique order number"
            
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
    

    # Generate unique order number
    @staticmethod
    def _generate_order_number(): 
        timestamp = datetime.now().strftime('%y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"ORD-{timestamp}{random_suffix}"
    

    # Get orders for a customer
    @staticmethod
    def get_customer_orders(customer_id, page=1, per_page=20, status_filter=None):
        
        try:
            order_model = Order()
            orders = order_model.get_by_customer(customer_id)
            
            # Apply status filter if provided
            if status_filter:
                orders = [o for o in orders if o.get('order_status') == status_filter]
            
            # Sort by created_at descending
            orders.sort(key=lambda x: x.get('created_at') or datetime.now().min, reverse=True)
            
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
    

    # Get order by ID with ownership check 
    @staticmethod
    def get_order_by_id(order_id, customer_id=None, session_id=None, include_items=True): 
        try:
            order_model = Order()
            
            # Use optimized query
            sql = """
                SELECT 
                    o.*,
                    c.customer_id,
                    c.username,
                    c.email,
                    c.first_name,
                    c.last_name
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.customer_id
                WHERE o.order_id = %s;
            """
            
            with get_cursor(commit=False) as cur:
                cur.execute(sql, (order_id,))
                order = cur.fetchone()
            
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
                order_data['customer'] = {
                    'customer_id': order['customer_id'],
                    'username': order['username'],
                    'email': order['email'],
                    'full_name': f"{order['first_name']} {order['last_name']}"
                }
            else:
                order_data['customer'] = 'Guest'
            
            # Add items if requested
            if include_items:
                items_sql = """
                    SELECT 
                        oi.order_item_id,
                        oi.quantity,
                        oi.unit_price,
                        oi.subtotal,
                        oi.design_file_url,
                        p.product_id,
                        p.product_name,
                        cat.category_name
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.product_id
                    JOIN categories cat ON p.category_id = cat.category_id
                    WHERE oi.order_id = %s;
                """
                
                with get_cursor(commit=False) as cur:
                    cur.execute(items_sql, (order_id,))
                    items_raw = cur.fetchall()
                
                items = []
                order_item_customization_model = OrderItemCustomization()
                
                for item in items_raw:
                    # Get customizations
                    customizations_raw = order_item_customization_model.get_by_order_item(
                        item['order_item_id']
                    )
                    customizations = {
                        c['customization_key']: c['customization_value']
                        for c in customizations_raw
                    } if customizations_raw else {}
                    
                    items.append({
                        'order_item_id': item['order_item_id'],
                        'product': {
                            'product_id': item['product_id'],
                            'product_name': item['product_name'],
                            'category_name': item['category_name']
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
    # Get order by order number
    @staticmethod
    def get_order_by_number(order_number, customer_id=None, session_id=None): 
        try:
            
            order_model = Order()
            
             
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
    

    #  Get order status with history
    @staticmethod
    def get_order_status(order_id, customer_id=None, session_id=None):
         
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
    
    #  Cancel an order
    @staticmethod
    def cancel_order(order_id, customer_id=None, session_id=None, reason=None):
         
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
    

    # Get customer's order statistics
    @staticmethod
    def get_customer_order_stats(customer_id):
         
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
    

    #  Update order status (admin only)
    @staticmethod
    def update_order_status(order_id, new_status, admin_id=None, notes=None):
         
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