"""
Admin Service
Business logic for admin operations
"""

from datetime import datetime, timedelta
from sqlalchemy import func

from app.database import get_db_session
from app.models.__models_init__ import (
    AdminUser, AdminActivityLog, Order, OrderItem,
    Customer, Product, Category
)
from app.utils.validators import Validators
from app.utils.helpers import PasswordHelper, DateHelper
from werkzeug.security import generate_password_hash


class AdminService:
    """Service class for admin operations"""
    
    @staticmethod
    def get_dashboard_stats():
        """
        Get admin dashboard statistics
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            with get_db_session() as db_session:
                # Get date ranges
                today = datetime.now().date()
                week_ago = today - timedelta(days=7)
                month_ago = today - timedelta(days=30)
                
                # Order statistics
                total_orders = db_session.query(Order).count()
                pending_orders = db_session.query(Order).filter_by(
                    order_status='pending'
                ).count()
                processing_orders = db_session.query(Order).filter_by(
                    order_status='processing'
                ).count()
                
                # Revenue statistics (completed/delivered orders only)
                total_revenue = db_session.query(
                    func.sum(Order.total_amount)
                ).filter(
                    Order.order_status.in_(['delivered', 'shipped', 'completed'])
                ).scalar() or 0
                
                month_revenue = db_session.query(
                    func.sum(Order.total_amount)
                ).filter(
                    Order.order_status.in_(['delivered', 'shipped', 'completed']),
                    func.date(Order.created_at) >= month_ago
                ).scalar() or 0
                
                week_revenue = db_session.query(
                    func.sum(Order.total_amount)
                ).filter(
                    Order.order_status.in_(['delivered', 'shipped', 'completed']),
                    func.date(Order.created_at) >= week_ago
                ).scalar() or 0
                
                # Customer statistics
                total_customers = db_session.query(Customer).count()
                active_customers = db_session.query(Customer).filter_by(
                    is_active=True
                ).count()
                new_customers_month = db_session.query(Customer).filter(
                    func.date(Customer.created_at) >= month_ago
                ).count()
                
                # Product statistics
                total_products = db_session.query(Product).count()
                active_products = db_session.query(Product).filter_by(
                    is_active=True
                ).count()
                
                # Recent orders
                recent_orders = db_session.query(Order).order_by(
                    Order.created_at.desc()
                ).limit(5).all()
                
                recent_orders_data = [
                    {
                        'order_id': o.order_id,
                        'order_number': o.order_number,
                        'customer_name': o.get_customer_name(),
                        'total_amount': float(o.total_amount),
                        'order_status': o.order_status,
                        'created_at': o.created_at.isoformat() if o.created_at else None
                    }
                    for o in recent_orders
                ]
                
                return {
                    'orders': {
                        'total': total_orders,
                        'pending': pending_orders,
                        'processing': processing_orders
                    },
                    'revenue': {
                        'total': float(total_revenue),
                        'month': float(month_revenue),
                        'week': float(week_revenue)
                    },
                    'customers': {
                        'total': total_customers,
                        'active': active_customers,
                        'new_this_month': new_customers_month
                    },
                    'products': {
                        'total': total_products,
                        'active': active_products
                    },
                    'recent_orders': recent_orders_data
                }
                
        except Exception as e:
            print(f"Error getting dashboard stats: {str(e)}")
            return {}
    
    @staticmethod
    def get_all_orders(status_filter=None, start_date=None, end_date=None,
                      page=1, per_page=20):
        """
        Get all orders with filtering
        
        Args:
            status_filter (str, optional): Filter by order status
            start_date (str, optional): Start date (ISO format)
            end_date (str, optional): End date (ISO format)
            page (int): Page number
            per_page (int): Items per page
            
        Returns:
            tuple: (orders_list, total_count, total_pages)
        """
        try:
            with get_db_session() as db_session:
                query = db_session.query(Order)
                
                # Apply filters
                if status_filter:
                    query = query.filter_by(order_status=status_filter)
                
                if start_date:
                    try:
                        start_dt = datetime.fromisoformat(start_date)
                        query = query.filter(Order.created_at >= start_dt)
                    except ValueError:
                        pass
                
                if end_date:
                    try:
                        end_dt = datetime.fromisoformat(end_date)
                        query = query.filter(Order.created_at <= end_dt)
                    except ValueError:
                        pass
                
                # Order by date (newest first)
                query = query.order_by(Order.created_at.desc())
                
                # Get total count
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                # Pagination
                offset = (page - 1) * per_page
                orders = query.offset(offset).limit(per_page).all()
                
                # Format results
                orders_list = [
                    {
                        'order_id': o.order_id,
                        'order_number': o.order_number,
                        'customer_name': o.get_customer_name(),
                        'customer_email': o.get_customer_email(),
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
            print(f"Error getting orders: {str(e)}")
            return [], 0, 0
    
    @staticmethod
    def get_all_customers(page=1, per_page=20, search_query=None):
        """
        Get all customers
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            search_query (str, optional): Search in username/email
            
        Returns:
            tuple: (customers_list, total_count, total_pages)
        """
        try:
            with get_db_session() as db_session:
                query = db_session.query(Customer).order_by(
                    Customer.created_at.desc()
                )
                
                # Apply search if provided
                if search_query:
                    from sqlalchemy import or_
                    pattern = f"%{search_query}%"
                    query = query.filter(
                        or_(
                            Customer.username.ilike(pattern),
                            Customer.email.ilike(pattern),
                            Customer.first_name.ilike(pattern),
                            Customer.last_name.ilike(pattern)
                        )
                    )
                
                # Get total count
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                # Pagination
                offset = (page - 1) * per_page
                customers = query.offset(offset).limit(per_page).all()
                
                # Format results
                customers_list = [
                    {
                        'customer_id': c.customer_id,
                        'username': c.username,
                        'email': c.email,
                        'full_name': c.full_name,
                        'phone_number': c.phone_number,
                        'is_active': c.is_active,
                        'total_orders': c.get_order_count(),
                        'total_spent': float(c.get_total_spent()),
                        'created_at': c.created_at.isoformat() if c.created_at else None,
                        'last_login': c.last_login.isoformat() if c.last_login else None
                    }
                    for c in customers
                ]
                
                return customers_list, total_count, total_pages
                
        except Exception as e:
            print(f"Error getting customers: {str(e)}")
            return [], 0, 0
    
    @staticmethod
    def get_all_products_admin(page=1, per_page=20, category_id=None, 
                               include_inactive=False):
        """
        Get all products (admin view)
        
        Args:
            page (int): Page number
            per_page (int): Items per page
            category_id (int, optional): Filter by category
            include_inactive (bool): Include inactive products
            
        Returns:
            tuple: (products_list, total_count, total_pages)
        """
        try:
            with get_db_session() as db_session:
                query = db_session.query(Product)
                
                if not include_inactive:
                    query = query.filter_by(is_active=True)
                
                if category_id:
                    query = query.filter_by(category_id=category_id)
                
                query = query.order_by(Product.product_name.asc())
                
                # Get total count
                total_count = query.count()
                total_pages = (total_count + per_page - 1) // per_page
                
                # Pagination
                offset = (page - 1) * per_page
                products = query.offset(offset).limit(per_page).all()
                
                # Format results
                products_list = [
                    {
                        'product_id': p.product_id,
                        'product_name': p.product_name,
                        'description': p.description,
                        'base_price': float(p.base_price),
                        'category_name': p.category.category_name,
                        'is_active': p.is_active,
                        'times_ordered': p.get_times_ordered(),
                        'created_at': p.created_at.isoformat() if p.created_at else None,
                        'updated_at': p.updated_at.isoformat() if p.updated_at else None
                    }
                    for p in products
                ]
                
                return products_list, total_count, total_pages
                
        except Exception as e:
            print(f"Error getting products: {str(e)}")
            return [], 0, 0
    
    @staticmethod
    def update_product_admin(product_id, admin_id, **kwargs):
        """
        Update product (admin only)
        
        Args:
            product_id (int): Product ID
            admin_id (int): Admin ID making the change
            **kwargs: Fields to update
            
        Returns:
            tuple: (success: bool, message)
        """
        allowed_fields = ['product_name', 'description', 'base_price', 
                         'is_active', 'category_id']
        
        try:
            with get_db_session() as db_session:
                product = db_session.query(Product).filter_by(
                    product_id=product_id
                ).first()
                
                if not product:
                    return False, "Product not found"
                
                # Store old values for audit log
                old_values = {
                    'product_name': product.product_name,
                    'base_price': float(product.base_price),
                    'is_active': product.is_active
                }
                
                # Validate and update fields
                update_data = {}
                for key, value in kwargs.items():
                    if key not in allowed_fields:
                        continue
                    
                    if key == 'base_price':
                        valid, msg = Validators.validate_price(value)
                        if not valid:
                            return False, msg
                        value = float(value)
                    
                    elif key in ('product_name', 'description'):
                        value = Validators.sanitize_string(value)
                    
                    setattr(product, key, value)
                    update_data[key] = value
                
                product.updated_at = DateHelper.now()
                product.updated_by = admin_id
                
                # Log activity
                activity_log = AdminActivityLog(
                    admin_id=admin_id,
                    action='update_product',
                    table_name='products',
                    record_id=product_id,
                    old_values=str(old_values),
                    new_values=str(update_data)
                )
                db_session.add(activity_log)
                
                db_session.commit()
                
                return True, "Product updated successfully"
                
        except Exception as e:
            return False, f"Failed to update product: {str(e)}"
    
    @staticmethod
    def create_admin_user(super_admin_id, username, email, password,
                         first_name, last_name, role='staff'):
        """
        Create new admin user (super_admin only)
        
        Args:
            super_admin_id (int): Super admin creating the user
            username (str): Admin username
            email (str): Admin email
            password (str): Admin password
            first_name (str): First name
            last_name (str): Last name
            role (str): Admin role (super_admin, admin, staff)
            
        Returns:
            tuple: (success: bool, admin or error_message)
        """
        # Validate inputs
        if not Validators.validate_username(username):
            return False, "Invalid username format"
        
        if not Validators.validate_email(email):
            return False, "Invalid email format"
        
        is_valid, message = Validators.validate_password_strength(password)
        if not is_valid:
            return False, message
        
        if not Validators.validate_role(role):
            return False, "Invalid role"
        
        try:
            with get_db_session() as db_session:
                # Check if username exists
                if db_session.query(AdminUser).filter_by(
                    username=username.lower()
                ).first():
                    return False, "Username already exists"
                
                # Check if email exists
                if db_session.query(AdminUser).filter_by(
                    email=email.lower()
                ).first():
                    return False, "Email already exists"
                
                # Create admin user
                admin = AdminUser(
                    username=username.lower(),
                    email=email.lower(),
                    password_hash=generate_password_hash(password),
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=True
                )
                db_session.add(admin)
                db_session.flush()
                
                # Log activity
                activity_log = AdminActivityLog(
                    admin_id=super_admin_id,
                    action='create_admin',
                    table_name='admin_users',
                    record_id=admin.admin_id,
                    new_values=f"Created {role} user: {username}"
                )
                db_session.add(activity_log)
                
                db_session.commit()
                
                return True, admin
                
        except Exception as e:
            return False, f"Failed to create admin user: {str(e)}"
    
    @staticmethod
    def get_sales_report(start_date=None, end_date=None):
        """
        Get sales report
        
        Args:
            start_date (str, optional): Start date (ISO format)
            end_date (str, optional): End date (ISO format)
            
        Returns:
            dict: Sales statistics
        """
        try:
            with get_db_session() as db_session:
                query = db_session.query(Order).filter(
                    Order.order_status.in_(['delivered', 'shipped', 'completed'])
                )
                
                if start_date:
                    try:
                        start_dt = datetime.fromisoformat(start_date)
                        query = query.filter(Order.created_at >= start_dt)
                    except ValueError:
                        pass
                
                if end_date:
                    try:
                        end_dt = datetime.fromisoformat(end_date)
                        query = query.filter(Order.created_at <= end_dt)
                    except ValueError:
                        pass
                
                orders = query.all()
                
                # Calculate statistics
                total_revenue = sum(float(o.total_amount) for o in orders)
                total_orders = len(orders)
                avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
                
                return {
                    'total_revenue': total_revenue,
                    'total_orders': total_orders,
                    'average_order_value': avg_order_value,
                    'start_date': start_date,
                    'end_date': end_date
                }
                
        except Exception as e:
            print(f"Error generating sales report: {str(e)}")
            return {}
    
    @staticmethod
    def get_product_report():
        """
        Get product performance report
        
        Returns:
            dict: Product statistics
        """
        try:
            with get_db_session() as db_session:
                products = db_session.query(Product).all()
                
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
                
                return {
                    'products': product_data[:20],  # Top 20
                    'total_products': len(products)
                }
                
        except Exception as e:
            print(f"Error generating product report: {str(e)}")
            return {}
    
    @staticmethod
    def log_admin_activity(admin_id, action, table_name=None, 
                          record_id=None, old_values=None, new_values=None):
        """
        Log admin activity
        
        Args:
            admin_id (int): Admin ID
            action (str): Action performed
            table_name (str, optional): Table affected
            record_id (int, optional): Record ID affected
            old_values (str, optional): Old values
            new_values (str, optional): New values
            
        Returns:
            bool: Success status
        """
        try:
            with get_db_session() as db_session:
                activity_log = AdminActivityLog(
                    admin_id=admin_id,
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_values=str(old_values) if old_values else None,
                    new_values=str(new_values) if new_values else None
                )
                db_session.add(activity_log)
                db_session.commit()
                return True
        except Exception as e:
            print(f"Error logging admin activity: {str(e)}")
            return False