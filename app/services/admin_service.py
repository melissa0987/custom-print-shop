"""
Admin Service
Business logic for admin panel operations
"""

from datetime import datetime, timedelta
from sqlalchemy import func

from app.database import get_db_session
from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)


class AdminService:
    """Service class for admin operations"""
    
    @staticmethod
    def get_dashboard_stats():
        """
        Get dashboard statistics
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            with get_db_session() as session:
                # Date ranges
                today = datetime.now().date()
                week_ago = today - timedelta(days=7)
                month_ago = today - timedelta(days=30)
                
                # Order statistics
                total_orders = session.query(Order).count()
                pending_orders = session.query(Order).filter_by(
                    order_status='pending'
                ).count()
                processing_orders = session.query(Order).filter_by(
                    order_status='processing'
                ).count()
                
                # Revenue statistics
                total_revenue = session.query(
                    func.sum(Order.total_amount)
                ).filter_by(order_status='completed').scalar() or 0
                
                month_revenue = session.query(
                    func.sum(Order.total_amount)
                ).filter(
                    Order.order_status == 'completed',
                    func.date(Order.created_at) >= month_ago
                ).scalar() or 0
                
                # Customer statistics
                total_customers = session.query(Customer).count()
                active_customers = session.query(Customer).filter_by(
                    is_active=True
                ).count()
                
                # Product statistics
                total_products = session.query(Product).count()
                active_products = session.query(Product).filter_by(
                    is_active=True
                ).count()
                
                return {
                    'orders': {
                        'total': total_orders,
                        'pending': pending_orders,
                        'processing': processing_orders
                    },
                    'revenue': {
                        'total': float(total_revenue),
                        'month': float(month_revenue)
                    },
                    'customers': {
                        'total': total_customers,
                        'active': active_customers
                    },
                    'products': {
                        'total': total_products,
                        'active': active_products
                    }
                }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return {}
    
    @staticmethod
    def get_all_orders(status=None, start_date=None, end_date=None, 
                       page=1, per_page=20):
        """
        Get all orders with filtering
        
        Args:
            status (str, optional): Filter by status
            start_date (datetime, optional): Start date
            end_date (datetime, optional): End date
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (orders, total_count, total_pages)
        """
        try:
            with get_db_session() as session:
                query = session.query(Order)
                
                if status:
                    query = query.filter_by(order_status=status)
                
                if start_date:
                    query = query.filter(Order.created_at >= start_date)
                if end_date:
                    query = query.filter(Order.created_at <= end_date)
                
                query = query.order_by(Order.created_at.desc())
                
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                offset = (page - 1) * per_page
                orders = query.offset(offset).limit(per_page).all()
                
                return orders, total_count, total_pages
                
        except Exception:
            return [], 0, 0
    
    @staticmethod
    def update_order_status(admin_id, order_id, new_status, notes=None):
        """
        Update order status
        
        Args:
            admin_id (int): Admin ID
            order_id (int): Order ID
            new_status (str): New status
            notes (str, optional): Status change notes
            
        Returns:
            tuple: (success: bool, message)
        """
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return False, "Invalid status"
        
        try:
            with get_db_session() as session:
                order = session.query(Order).filter_by(order_id=order_id).first()
                
                if not order:
                    return False, "Order not found"
                
                old_status = order.order_status
                
                # Update order
                order.order_status = new_status
                order.updated_at = datetime.now()
                order.updated_by = admin_id
                
                # Add status history
                status_history = OrderStatusHistory(
                    order_id=order_id,
                    status=new_status,
                    changed_by=admin_id,
                    notes=notes
                )
                session.add(status_history)
                
                # Log activity
                activity_log = AdminActivityLog(
                    admin_id=admin_id,
                    action='update_order_status',
                    table_name='orders',
                    record_id=order_id,
                    old_values={'order_status': old_status},
                    new_values={'order_status': new_status, 'notes': notes}
                )
                session.add(activity_log)
                
                return True, "Order status updated successfully"
                
        except Exception as e:
            return False, f"Failed to update order status: {str(e)}"
    
    @staticmethod
    def get_all_customers(page=1, per_page=20):
        """
        Get all customers
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (customers, total_count, total_pages)
        """
        try:
            with get_db_session() as session:
                query = session.query(Customer).order_by(Customer.created_at.desc())
                
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                offset = (page - 1) * per_page
                customers = query.offset(offset).limit(per_page).all()
                
                return customers, total_count, total_pages
                
        except Exception:
            return [], 0, 0
    
    @staticmethod
    def get_customer_details(customer_id):
        """
        Get customer details with statistics
        
        Args:
            customer_id (int): Customer ID
            
        Returns:
            dict or None: Customer details and statistics
        """
        try:
            with get_db_session() as session:
                customer = session.query(Customer).filter_by(
                    customer_id=customer_id
                ).first()
                
                if not customer:
                    return None
                
                return {
                    'customer_id': customer.customer_id,
                    'username': customer.username,
                    'email': customer.email,
                    'full_name': customer.full_name,
                    'phone_number': customer.phone_number,
                    'is_active': customer.is_active,
                    'created_at': customer.created_at,
                    'last_login': customer.last_login,
                    'total_orders': customer.get_order_count(),
                    'total_spent': float(customer.get_total_spent())
                }
        except Exception:
            return None
    
    @staticmethod
    def get_sales_report(start_date=None, end_date=None):
        """
        Get sales report
        
        Args:
            start_date (datetime, optional): Start date
            end_date (datetime, optional): End date
            
        Returns:
            dict: Sales statistics
        """
        try:
            with get_db_session() as session:
                query = session.query(Order).filter_by(order_status='completed')
                
                if start_date:
                    query = query.filter(Order.created_at >= start_date)
                if end_date:
                    query = query.filter(Order.created_at <= end_date)
                
                orders = query.all()
                
                total_revenue = sum(float(o.total_amount) for o in orders)
                total_orders = len(orders)
                avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
                
                return {
                    'total_revenue': total_revenue,
                    'total_orders': total_orders,
                    'average_order_value': avg_order_value,
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
        except Exception:
            return {}
    
    @staticmethod
    def get_product_report():
        """
        Get product performance report
        
        Returns:
            list: Product statistics
        """
        try:
            with get_db_session() as session:
                products = session.query(Product).all()
                
                product_data = []
                for product in products:
                    product_data.append({
                        'product_id': product.product_id,
                        'product_name': product.product_name,
                        'category_name': product.category.category_name,
                        'base_price': float(product.base_price),
                        'times_ordered': product.get_times_ordered(),
                        'total_quantity_sold': product.get_total_quantity_sold(),
                        'total_revenue': float(product.get_total_revenue() or 0)
                    })
                
                # Sort by revenue
                product_data.sort(key=lambda x: x['total_revenue'], reverse=True)
                
                return product_data
        except Exception:
            return []
    
    @staticmethod
    def log_admin_activity(admin_id, action, table_name, record_id, 
                          old_values=None, new_values=None, ip_address=None):
        """
        Log admin activity
        
        Args:
            admin_id (int): Admin ID
            action (str): Action performed
            table_name (str): Table affected
            record_id (int): Record ID
            old_values (dict, optional): Old values
            new_values (dict, optional): New values
            ip_address (str, optional): IP address
            
        Returns:
            bool: Success status
        """
        try:
            with get_db_session() as session:
                activity_log = AdminActivityLog(
                    admin_id=admin_id,
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=ip_address
                )
                session.add(activity_log)
                return True
        except Exception as e:
            print(f"Error logging activity: {e}")
            return False
    
    @staticmethod
    def get_recent_activity(admin_id=None, limit=50):
        """
        Get recent admin activity
        
        Args:
            admin_id (int, optional): Filter by admin ID
            limit (int): Maximum results
            
        Returns:
            list: Activity log records
        """
        try:
            with get_db_session() as session:
                query = session.query(AdminActivityLog)
                
                if admin_id:
                    query = query.filter_by(admin_id=admin_id)
                
                return query.order_by(
                    AdminActivityLog.created_at.desc()
                ).limit(limit).all()
        except Exception:
            return []
    
    @staticmethod
    def get_all_products(category_id=None, is_active=None, page=1, per_page=20):
        """
        Get all products for admin
        
        Args:
            category_id (int, optional): Filter by category
            is_active (bool, optional): Filter by active status
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (products, total_count, total_pages)
        """
        try:
            with get_db_session() as session:
                query = session.query(Product)
                
                if category_id:
                    query = query.filter_by(category_id=category_id)
                
                if is_active is not None:
                    query = query.filter_by(is_active=is_active)
                
                query = query.order_by(Product.product_name)
                
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                offset = (page - 1) * per_page
                products = query.offset(offset).limit(per_page).all()
                
                return products, total_count, total_pages
                
        except Exception:
            return [], 0, 0
    
    @staticmethod
    def update_product(admin_id, product_id, **kwargs):
        """
        Update product
        
        Args:
            admin_id (int): Admin ID
            product_id (int): Product ID
            **kwargs: Fields to update
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                product = session.query(Product).filter_by(
                    product_id=product_id
                ).first()
                
                if not product:
                    return False, "Product not found"
                
                # Store old values
                old_values = {
                    'product_name': product.product_name,
                    'base_price': float(product.base_price),
                    'is_active': product.is_active
                }
                
                # Update fields
                allowed_fields = ['product_name', 'description', 'base_price', 
                                'is_active', 'category_id']
                for field in allowed_fields:
                    if field in kwargs:
                        setattr(product, field, kwargs[field])
                
                product.updated_at = datetime.now()
                product.updated_by = admin_id
                
                # Log activity
                AdminService.log_admin_activity(
                    admin_id, 'update_product', 'products',
                    product_id, old_values, kwargs
                )
                
                return True, "Product updated successfully"
                
        except Exception as e:
            return False, f"Failed to update product: {str(e)}"
    
    @staticmethod
    def deactivate_customer(admin_id, customer_id):
        """
        Deactivate customer account
        
        Args:
            admin_id (int): Admin ID
            customer_id (int): Customer ID
            
        Returns:
            tuple: (success: bool, message)
        """
        try:
            with get_db_session() as session:
                customer = session.query(Customer).filter_by(
                    customer_id=customer_id
                ).first()
                
                if not customer:
                    return False, "Customer not found"
                
                customer.is_active = False
                
                # Log activity
                AdminService.log_admin_activity(
                    admin_id, 'deactivate_customer', 'customers',
                    customer_id, {'is_active': True}, {'is_active': False}
                )
                
                return True, "Customer deactivated successfully"
                
        except Exception as e:
            return False, f"Failed to deactivate customer: {str(e)}"