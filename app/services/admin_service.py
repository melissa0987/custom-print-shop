"""
app/services/admin_service.py
Admin Service
Business logic for admin operations

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
    
    # Get admin dashboard statistics
    @staticmethod
    def get_dashboard_stats(): 
        try:
            order_model = Order()
            customer_model = Customer()
            product_model = Product()
            
            # Get date ranges
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30) 
            all_orders = []  
            
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
    

    # Get all orders with filtering 
    @staticmethod
    def get_all_orders(status_filter=None, start_date=None, end_date=None,
                    page=1, per_page=20): 
        try:
            order_model = Order()
            orders = order_model.get_all()
            
            # Filter by status
            if status_filter:
                orders = [o for o in orders if o.get('order_status') == status_filter]
            
            # Filter by date range
            if start_date:
                start = DateHelper.parse_date(start_date) if isinstance(start_date, str) else start_date
                orders = [o for o in orders if o.get('created_at') and o['created_at'].date() >= start]
            
            if end_date:
                end = DateHelper.parse_date(end_date) if isinstance(end_date, str) else end_date
                orders = [o for o in orders if o.get('created_at') and o['created_at'].date() <= end]
            
            # Pagination
            total_count = len(orders)
            total_pages = (total_count + per_page - 1) // per_page
            offset = (page - 1) * per_page
            orders = orders[offset:offset + per_page]
            
            return orders, total_count, total_pages
                
        except Exception as e:
            print(f"Error getting orders: {str(e)}")
            return [], 0, 0
    

    # Get all customers
    @staticmethod
    def get_all_customers(page=1, per_page=20, search_query=None): 
        try:
            customer_model = Customer()
            customers = customer_model.get_all()
            
            # Search filter
            if search_query:
                search_lower = search_query.lower()
                customers = [
                    c for c in customers
                    if search_lower in c.get('username', '').lower() or
                    search_lower in c.get('email', '').lower() or
                    search_lower in c.get('first_name', '').lower() or
                    search_lower in c.get('last_name', '').lower()
                ]
            
            # Pagination
            total_count = len(customers)
            total_pages = (total_count + per_page - 1) // per_page
            offset = (page - 1) * per_page
            customers = customers[offset:offset + per_page]
            
            return customers, total_count, total_pages
                
        except Exception as e:
            print(f"Error getting customers: {str(e)}")
            return [], 0, 0
    

    # Get all products (admin view)
    @staticmethod
    def get_all_products_admin(page=1, per_page=20, category_id=None,  include_inactive=False): 
        
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
    

    # Update product (admin only)
    @staticmethod
    def update_product_admin(product_id, admin_id, **kwargs):
        
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
    

    # Create new admin user (super_admin only)
    @staticmethod
    def create_admin_user(super_admin_id, username, email, password, first_name, last_name, role='staff'): 
        
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
    

    # Get sales report 
    @staticmethod
    def get_sales_report(start_date=None, end_date=None): 
        try:
            order_model = Order()
            orders = order_model.get_all()
            
            # Filter by date range
            if start_date:
                start = DateHelper.parse_date(start_date) if isinstance(start_date, str) else start_date
                orders = [o for o in orders if o.get('created_at') and o['created_at'].date() >= start]
            
            if end_date:
                end = DateHelper.parse_date(end_date) if isinstance(end_date, str) else end_date
                orders = [o for o in orders if o.get('created_at') and o['created_at'].date() <= end]
            
            # Calculate metrics
            completed_orders = [o for o in orders if o.get('order_status') == 'completed']
            total_revenue = sum(float(o.get('total_amount', 0)) for o in completed_orders)
            total_orders = len(orders)
            average_order_value = total_revenue / len(completed_orders) if completed_orders else 0.0
            
            return {
                'total_revenue': total_revenue,
                'total_orders': total_orders,
                'average_order_value': average_order_value,
                'completed_orders': len(completed_orders),
                'pending_orders': sum(1 for o in orders if o.get('order_status') == 'pending'),
                'start_date': start_date,
                'end_date': end_date
            }
                
        except Exception as e:
            print(f"Error generating sales report: {str(e)}")
            return {}
    
    # Get product performance report
    @staticmethod
    def get_product_report(): 
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
    

    # Log admin activity
    @staticmethod
    def log_admin_activity(admin_id, action, table_name=None,  record_id=None, old_values=None, new_values=None): 
        
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