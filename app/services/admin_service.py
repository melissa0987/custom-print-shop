"""
Admin Service
Business logic for admin operations
Updated to use psycopg2-based models
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app.models import (
    AdminUser, AdminActivityLog, Order, OrderItem,
    Customer, Product, Category
)
from app.utils.validators import Validators
from app.utils.helpers import PasswordHelper, DateHelper


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
            order_model = Order()
            customer_model = Customer()
            product_model = Product()
            
            # Get date ranges
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Get all orders
            # Note: This is inefficient for large datasets
            # Consider adding date filtering methods to Order model
            all_orders = []
            # You'll need a way to get all orders - may need to add to model
            
            # For now, return basic stats
            # This needs proper implementation based on your Order model capabilities
            
            return {
                'orders': {
                    'total': 0,
                    'pending': 0,
                    'processing': 0
                },
                'revenue': {
                    'total': 0.0,
                    'month': 0.0,
                    'week': 0.0
                },
                'customers': {
                    'total': 0,
                    'active': 0,
                    'new_this_month': 0
                },
                'products': {
                    'total': len(product_model.get_all()),
                    'active': len(product_model.get_all(active_only=True))
                },
                'recent_orders': []
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
            # Note: This implementation is limited by the Order model capabilities
            # You may need to add methods to get all orders
            
            return [], 0, 0
                
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
            # Note: This requires a method to get all customers
            # Your Customer model doesn't have get_all() method
            
            return [], 0, 0
                
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
            product_model = Product()
            category_model = Category()
            
            # Get products
            products = product_model.get_all(active_only=not include_inactive)
            
            # Filter by category if specified
            if category_id:
                products = [p for p in products if p.get('category_id') == category_id]
            
            # Sort by product name
            products.sort(key=lambda x: x.get('product_name', '').lower())
            
            # Pagination
            total_count = len(products)
            total_pages = (total_count + per_page - 1) // per_page
            offset = (page - 1) * per_page
            products = products[offset:offset + per_page]
            
            # Format results
            products_list = []
            for p in products:
                category = category_model.get_by_id(p['category_id'])
                
                products_list.append({
                    'product_id': p['product_id'],
                    'product_name': p['product_name'],
                    'description': p.get('description'),
                    'base_price': float(p['base_price']),
                    'category_name': category['category_name'] if category else 'Unknown',
                    'is_active': p.get('is_active'),
                    'times_ordered': product_model.get_total_orders(p['product_id']),
                    'created_at': p['created_at'].isoformat() if p.get('created_at') else None,
                    'updated_at': p['updated_at'].isoformat() if p.get('updated_at') else None
                })
            
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
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product:
                return False, "Product not found"
            
            # Store old values for audit log
            old_values = {
                'product_name': product['product_name'],
                'base_price': float(product['base_price']),
                'is_active': product.get('is_active')
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
                
                update_data[key] = value
            
            update_data['updated_by'] = admin_id
            
            # Update product
            product_model.update(product_id, **update_data)
            
            # Log activity
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=admin_id,
                action='update_product',
                table_name='products',
                record_id=product_id,
                old_values=old_values,
                new_values=update_data
            )
            
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
            admin_model = AdminUser()
            
            # Check if username exists
            if admin_model.get_by_username(username.lower()):
                return False, "Username already exists"
            
            # Check if email exists (you may need to add get_by_email method)
            # For now, skip email check
            
            # Create admin user
            admin_id = admin_model.create(
                username=username.lower(),
                email=email.lower(),
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                created_by=super_admin_id
            )
            
            # Log activity
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=super_admin_id,
                action='create_admin',
                table_name='admin_users',
                record_id=admin_id,
                new_values=f"Created {role} user: {username}"
            )
            
            # Get created admin
            admin = admin_model.get_by_id(admin_id)
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
            # This requires filtering orders by date
            # Your Order model may not support this yet
            
            return {
                'total_revenue': 0.0,
                'total_orders': 0,
                'average_order_value': 0.0,
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
            product_model = Product()
            category_model = Category()
            products = product_model.get_all()
            
            product_data = []
            for product in products:
                category = category_model.get_by_id(product['category_id'])
                
                product_data.append({
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'category_name': category['category_name'] if category else 'Unknown',
                    'base_price': float(product['base_price']),
                    'times_ordered': product_model.get_total_orders(product['product_id']),
                    'total_quantity_sold': product_model.get_total_quantity_sold(product['product_id']),
                    'total_revenue': product_model.get_total_revenue(product['product_id'])
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
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=admin_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values
            )
            return True
        except Exception as e:
            print(f"Error logging admin activity: {str(e)}")
            return False