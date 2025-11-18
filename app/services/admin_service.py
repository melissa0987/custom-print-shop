"""
app/services/admin_service.py
Admin Service
Business logic for admin operations

"""

from datetime import datetime, timedelta
import os
 
from flask import current_app, session, url_for
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename 

from app.models import (
    AdminUser, AdminActivityLog, Order, OrderItem,
    Customer, Product, Category
)
from app.models.order_status_history import OrderStatusHistory
from app.services.customer_service import CustomerService
from app.utils.image_helpers import ImageHelper
from app.utils.validators import Validators
from app.utils.helpers import PaginationHelper, PasswordHelper, DateHelper, PriceHelper, StringHelper


class AdminService: 
    VALID_STATUSES = ['pending', 'processing', 'completed', 'cancelled'] 
    
    # Get admin dashboard statistics
    @staticmethod
    def get_dashboard_stats():
        try:
            order_model = Order()
            customer_model = Customer()
            product_model = Product()

            # Fetch everything once
            all_orders = order_model.get_all()
            all_customers = customer_model.get_all()
            all_products = product_model.get_all(active_only=False)

            # Maps for quick lookup
            customer_map = {c['customer_id']: c for c in all_customers}

            today = datetime.now().date()
            month_start = today.replace(day=1)
            week_start = today - timedelta(days=today.weekday())

            # -----------------------------
            # ORDER STATS
            # -----------------------------
            total_orders = len(all_orders)
            pending_orders = sum(1 for o in all_orders if o['order_status'] == 'pending')
            processing_orders = sum(1 for o in all_orders if o['order_status'] == 'processing')

            # -----------------------------
            # REVENUE STATS
            # -----------------------------
            total_revenue = sum(float(o['total_amount']) for o in all_orders)

            month_revenue = sum(
                float(o['total_amount'])
                for o in all_orders
                if o['created_at'].date() >= month_start
            )

            week_revenue = sum(
                float(o['total_amount'])
                for o in all_orders
                if o['created_at'].date() >= week_start
            )

            # -----------------------------
            # CUSTOMER STATS
            # -----------------------------
            total_customers = len(all_customers)
            active_customers = sum(1 for c in all_customers if c.get('is_active'))
            new_this_month = sum(
                1 for c in all_customers
                if c.get('created_at') and c['created_at'].date() >= month_start
            )

            # -----------------------------
            # PRODUCT STATS
            # -----------------------------
            total_products = len(all_products)
            active_products = sum(1 for p in all_products if p.get('is_active'))

            # -----------------------------
            # RECENT ORDERS (with customer)
            # -----------------------------
            enriched_orders = []
            for o in all_orders:
                cust = customer_map.get(o['customer_id'])
                o_copy = dict(o)
                o_copy['customer_name'] = (
                    f"{cust['first_name']} {cust['last_name']}"
                    if cust else "N/A"
                )
                enriched_orders.append(o_copy)

            recent_orders = sorted(
                enriched_orders,
                key=lambda o: o['created_at'],
                reverse=True
            )[:5]

            # -----------------------------
            # RETURN STRUCTURE
            # -----------------------------
            return {
                'orders': {
                    'total': total_orders,
                    'pending': pending_orders,
                    'processing': processing_orders
                },
                'revenue': {
                    'total': total_revenue,
                    'month': month_revenue,
                    'week': week_revenue
                },
                'customers': {
                    'total': total_customers,
                    'active': active_customers,
                    'new_this_month': new_this_month
                },
                'products': {
                    'total': total_products,
                    'active': active_products
                },
                'recent_orders': recent_orders
            }

        except Exception as e:
            print(f"Error getting dashboard stats: {str(e)}")
            return {}
    

# ============================================
# ORDER MANAGEMENT
# ============================================
    # Get all orders with filtering 
    @staticmethod
    def get_all_orders(status_filter=None, start_date=None, end_date=None,
                       page=1, per_page=20, search_term=None): 
        try:
            order_model = Order()
            customer_model = Customer()
            orders = order_model.get_all() if hasattr(order_model, 'get_all') else []

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

            # Enrich orders with customer info
            all_customers = customer_model.get_all()
            customer_map = {c['customer_id']: c for c in all_customers}
            formatted_orders = []
            for order in orders:
                customer_username = 'Guest'
                customer_email = order.get('contact_email')

                if order.get('customer_id'):
                    customer = customer_map.get(order['customer_id'])
                    if customer:
                        customer_username = customer['username']
                        customer_email = customer['email']

                order_data = {
                    'order_id': order['order_id'],
                    'order_number': order['order_number'],
                    'customer_username': customer_username,
                    'customer_email': customer_email,
                    'order_status': order['order_status'],
                    'total_amount': float(order['total_amount']),
                    'created_at': order.get('created_at'),
                    'updated_at': order.get('updated_at')
                }

                # Apply search filter
                if search_term:
                    search_lower = search_term.lower()
                    if not (
                        (order_data['order_number'] and search_lower in order_data['order_number'].lower()) or
                        (customer_username and search_lower in customer_username.lower()) or
                        (customer_email and search_lower in customer_email.lower())
                    ):
                        continue

                formatted_orders.append(order_data)

            # Sort by created_at descending
            formatted_orders.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)

            # Pagination
            total_count = len(formatted_orders)
            total_pages = (total_count + per_page - 1) // per_page
            offset = (page - 1) * per_page
            paginated_orders = formatted_orders[offset:offset + per_page]

            return paginated_orders, total_count, total_pages

        except Exception as e:
            print(f"Error getting orders: {str(e)}")
            return [], 0, 0
    
    @staticmethod
    def get_order_details(order_id): 
        order_model = Order()
        order_item_model = OrderItem()
        product_model = Product()
        category_model = Category()
        order_status_history_model = OrderStatusHistory()

        order = order_model.get_by_id(order_id)
        if not order:
            raise Exception(f"Order ID {order_id} not found")

        # Raw datetime objects
        raw_created_at = order.get('created_at')
        raw_updated_at = order.get('updated_at')

        # Base order data
        order_data = {
            'order_id': order['order_id'],
            'order_number': order['order_number'],
            'order_status': order['order_status'],
            'total_amount': float(order['total_amount']),
            'shipping_address': order.get('shipping_address'),
            'contact_phone': order.get('contact_phone'),
            'contact_email': order.get('contact_email'),
            'notes': order.get('notes'),
            'created_at': raw_created_at,
            'updated_at': raw_updated_at
        }

        # Customer info
        if order.get('customer_id'):
            customer = Customer().get_by_id(order['customer_id'])
            if customer:
                order_data['customer'] = {
                    'customer_id': customer['customer_id'],
                    'username': customer['username'],
                    'email': customer['email'],
                    'full_name': Customer().full_name(customer)
                }
            else:
                order_data['customer'] = 'Guest'
        else:
            order_data['customer'] = 'Guest'

        # Items
        items = []
        for oi in order_item_model.get_by_order(order_id):
            product = product_model.get_by_id(oi['product_id'])
            category = category_model.get_by_id(product['category_id'])
            customizations = {}
            raw_cust = oi.get('customizations', [])
            if isinstance(raw_cust, (list, tuple)):
                customizations = {c['customization_key']: c['customization_value'] for c in raw_cust}
            elif isinstance(raw_cust, dict):
                customizations = raw_cust

            items.append({
                'order_item_id': oi['order_item_id'],
                'product': {
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'category_name': category['category_name'],
                    'image_url': product.get('image_url')  # fallback added below
                },
                'quantity': oi['quantity'],
                'unit_price': float(oi['unit_price']),
                'subtotal': float(oi['subtotal']),
                'design_file_url': oi.get('design_file_url'),
                'customizations': customizations
            })
        order_data['items'] = items

        # Status history
        history = []
        for h in order_status_history_model.get_by_order(order_id) or []:
            history.append({
                'status': h.get('status'),
                'changed_at': h['changed_at'].isoformat() if h.get('changed_at') else None,
                'changed_by': order_status_history_model.get_changed_by_name(h),
                'notes': h.get('notes')
            })
        order_data['status_history'] = history

        # Root-level customer info
        if isinstance(order_data.get('customer'), dict):
            order_data['customer_name'] = order_data['customer'].get('full_name', 'Unknown')
            order_data['customer_email'] = order_data['customer'].get('email', 'N/A')
        else:
            order_data['customer_name'] = 'Guest'
            order_data['customer_email'] = order_data.get('contact_email', 'N/A')

        # Fallback images for products
        for item in order_data.get("items", []):
            pname = item["product"]["product_name"].lower()
            if not item["product"].get("image_url"):
                if 'mug' in pname:
                    img = '/static/images/products/mug.png'
                elif 'tote' in pname:
                    img = '/static/images/products/tote.png'
                elif 'drawstring' in pname:
                    img = '/static/images/products/drawstring-bag.png'
                elif 'shopping' in pname:
                    img = '/static/images/products/shopping-bag.png'
                elif 't-shirt' in pname or 'tshirt' in pname:
                    img = '/static/images/products/shirt.png'
                elif 'tumbler' in pname:
                    img = '/static/images/products/tumbler.png'
                else:
                    img = '/static/images/products/default.png'
                item["product"]["image_url"] = img

        return order_data


    @staticmethod
    def update_order_status(order_id, new_status, admin_id, notes=''): 
        if not new_status or new_status not in AdminService.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        order_model = Order()
        order = order_model.get_by_id(order_id)
        if not order:
            raise Exception(f"Order ID {order_id} not found")

        old_status = order['order_status']

        # Update status in DB
        order_model.update_status(order_id, new_status, updated_by=admin_id)

        # Log status history
        OrderStatusHistory().create(
            order_id=order_id,
            status=new_status,
            changed_by=admin_id,
            notes=notes
        )

        # Log admin activity
        AdminActivityLog().create_log(
            admin_id=admin_id,
            action='update_order_status',
            table_name='orders',
            record_id=order_id,
            old_values={'order_status': old_status},
            new_values={'order_status': new_status, 'notes': notes}
        )

        return {"order_id": order_id, "old_status": old_status, "new_status": new_status, "notes": notes}


# ============================================
# PRODUCT MANAGEMENT
# ============================================
    @staticmethod
    def get_products(category_id=None, search_term=None,
                     min_price=None, max_price=None,
                     page=1, per_page=20, sort_by='name', sort_order='asc'): 
        try:
            product_model = Product()
            category_model = Category()

            # Get all products (including inactive for admin)
            products = product_model.get_all(active_only=False)

            # --- Apply filters ---
            if category_id:
                products = [p for p in products if p.get('category_id') == category_id]

            if search_term:
                s = search_term.lower()
                products = [
                    p for p in products
                    if s in p.get('product_name', '').lower()
                    or s in p.get('description', '').lower()
                ]

            if min_price is not None:
                products = [p for p in products if float(p.get('base_price', 0)) >= min_price]
            if max_price is not None:
                products = [p for p in products if float(p.get('base_price', 0)) <= max_price]

            # --- Apply sorting ---
            if sort_by == 'price':
                products.sort(key=lambda x: float(x.get('base_price', 0)), reverse=(sort_order == 'desc'))
            elif sort_by == 'newest':
                products.sort(key=lambda x: x.get('created_at') or '', reverse=(sort_order == 'desc'))
            else:  # default: sort by name
                products.sort(key=lambda x: x.get('product_name', '').lower(), reverse=(sort_order == 'desc'))

            # --- Pagination ---
            paginated = PaginationHelper.paginate_list(products, page, per_page)

            # Format products with category info
            formatted_products = []
            for p in paginated['items']:
                category = category_model.get_by_id(p['category_id'])
                image_path = ImageHelper.get_product_image_url(p['product_id'], p['product_name'])
                image_url = url_for('static', filename=image_path)

                formatted_products.append({
                    'product_id': p['product_id'],
                    'product_name': p['product_name'],
                    'slug': StringHelper.slugify(p['product_name']),
                    'description': StringHelper.truncate_text(p.get('description'), 120),
                    'base_price': float(p['base_price']),
                    'base_price_formatted': PriceHelper.format_currency(p['base_price']),
                    'category': {
                        'category_id': category['category_id'],
                        'category_name': category['category_name']
                    } if category else None,
                    'image_url': image_url,
                    'is_active': p.get('is_active'),
                    'created_at': p['created_at'].isoformat() if p.get('created_at') else None
                })

            # Categories for filters
            categories = category_model.get_all()
            categories_for_template = [
                {'category_id': c['category_id'], 'category_name': c['category_name']} for c in categories
            ]

            pagination_data = {
                'page': paginated['page'],
                'per_page': paginated['per_page'],
                'total_items': paginated['total_items'],
                'total_pages': max(1, paginated['total_pages']),
                'has_next': paginated['page'] < paginated['total_pages'],
                'has_prev': paginated['page'] > 1
            }

            return {
                'products': formatted_products,
                'pagination': pagination_data,
                'categories': categories_for_template
            }

        except Exception as e:
            raise Exception(f"Error fetching products: {str(e)}")
        

    @staticmethod
    def create_product(data: dict, file=None): 
        required_fields = ['product_name', 'category_id', 'base_price']
        for field in required_fields:
            if not data.get(field):
                raise Exception(f"{field} is required")

        # create product first to get product_id
        product_id = Product().create(
            category_id=int(data['category_id']),
            product_name=data['product_name'],
            base_price=float(data['base_price']),
            description=data.get('description'),
            is_active=data.get('is_active') == 'on',
            created_by=session.get('admin_id')
        )

        # Ensure directories exist
        ImageHelper.ensure_directories()

        # Save uploaded image using product_id
        if file and ImageHelper.validate_image_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()

            # Main product image
            product_filename = f"product_{product_id}.{ext}"
            product_path = os.path.join(current_app.root_path, ImageHelper.PRODUCT_IMAGES_DIR, product_filename)
            file.save(product_path)

            # Mockup image
            mockup_filename = f"product_{product_id}_mockup.{ext}"
            mockup_path = os.path.join(current_app.root_path, ImageHelper.MOCKUPS_DIR, mockup_filename)
            file.seek(0)
            file.save(mockup_path)

            # Update product record with main image URL
            Product().update(product_id, image_url=f"{ImageHelper.PRODUCT_IMAGES_DIR}/{product_filename}")

        return product_id
    
    @staticmethod
    def get_product_detail(product_id: int): 
        product_model = Product()
        category_model = Category()

        
        product = product_model.get_by_id(product_id)
        if not product:
            raise Exception(f"Product with ID {product_id} not found.")

        
        category = category_model.get_by_id(product.get('category_id'))

        # Get product image URL
        image_path = ImageHelper.get_product_image_url(product['product_id'], product['product_name'])
        image_url = url_for('static', filename=image_path)

        # Format product data
        formatted_product = {
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'slug': StringHelper.slugify(product['product_name']),
            'description': product.get('description'),
            'base_price': float(product['base_price']),
            'base_price_formatted': PriceHelper.format_currency(product['base_price']),
            'category': {
                'category_id': category['category_id'],
                'category_name': category['category_name']
            } if category else None,
            'image_url': image_url,
            'is_active': product.get('is_active'),
            'created_at': product['created_at'].isoformat() if product.get('created_at') else None,
            'updated_at': product['updated_at'].isoformat() if product.get('updated_at') else None
        }

        # Fetch all categories for admin filter dropdown
        categories = category_model.get_all()

        return {'product': formatted_product, 'categories': categories}

    @staticmethod
    def toggle_product_status(product_id: int, admin_id: int): 
        product_model = Product()
        product = product_model.get_by_id(product_id)
        if not product:
            raise Exception("Product not found.")

        new_status = not product.get('is_active', True)
        success = product_model.update(
            product_id,
            is_active=new_status,
            updated_by=admin_id
        )
        if not success:
            raise Exception("Failed to update product status.")

        # Log admin activity
        AdminActivityLog().create_log(
            admin_id=admin_id,
            action='toggle_product_status',
            table_name='products',
            record_id=product_id,
            old_values={'is_active': product.get('is_active')},
            new_values={'is_active': new_status}
        )

        return new_status


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
            
             
            product_model.update(product_id, **update_data)
            
            # Log activity using single activity log instance
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
    def delete_product(product_id: int, admin_id: int): 
        product_model = Product()
        product = product_model.get_by_id(product_id)
        if not product:
            raise Exception("Product not found.")

        total_orders = product_model.get_total_orders(product_id)

        if total_orders > 0:
            # Soft delete
            success = product_model.update(
                product_id,
                is_active=False,
                updated_by=admin_id
            )
            if not success:
                raise Exception("Failed to deactivate product.")
            AdminActivityLog().create_log(
                admin_id=admin_id,
                action='soft_delete_product',
                table_name='products',
                record_id=product_id,
                old_values={'is_active': product.get('is_active')},
                new_values={'is_active': False}
            )
            return "Product has existing orders, so it was deactivated."
        else:
            # Hard delete
            success = product_model.delete(product_id)
            if not success:
                raise Exception("Failed to delete product.")
            AdminActivityLog().create_log(
                admin_id=admin_id,
                action='delete_product',
                table_name='products',
                record_id=product_id,
                old_values=None,
                new_values=None
            )
            return "Product deleted successfully."

    @staticmethod
    def update_product(product_id: int, data: dict, file=None, admin_id=None): 
        product_model = Product()
        product = product_model.get_by_id(product_id)
        if not product:
            raise Exception("Product not found.")

        # Update product fields
        updated_data = {
            'product_name': data.get('product_name'),
            'category_id': int(data.get('category_id')),
            'base_price': float(data.get('base_price')),
            'description': data.get('description'),
            'is_active': data.get('is_active') == 'on',
            'updated_by': admin_id
        }
        product_model.update(product_id, **updated_data)

        # Handle image
        if file and ImageHelper.validate_image_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{product_id}_{secure_filename(data['product_name'])}.{ext}"
            path = os.path.join(current_app.root_path, ImageHelper.PRODUCT_IMAGES_DIR, filename)
            file.save(path)
            product_model.update(product_id, image_url=f"{ImageHelper.PRODUCT_IMAGES_DIR}/{filename}")



# ============================================
# CUSTOMER MANAGEMENT
# ============================================
 
    @staticmethod
    def toggle_customer_status(customer_id): 
        customer_model = Customer()
        activity_log_model = AdminActivityLog()

        customer = customer_model.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        old_status = customer.get('is_active', True)
        new_status = not old_status

        success = customer_model.update(customer_id, is_active=new_status, updated_by=session.get('admin_id'))
        if success:
            activity_log_model.create_log(
                admin_id=session['admin_id'],
                action='toggle_customer_status',
                table_name='customers',
                record_id=customer_id,
                old_values={'is_active': old_status},
                new_values={'is_active': new_status}
            )

        return success, new_status


    @staticmethod
    def update_customer_as_admin(customer_id, data): 
        customer_model = Customer()
        customer_service = CustomerService()

        # Fetch existing customer
        customer = customer_model.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        update_data = {}

        # Only update password if provided, blank keeps the old password
        password = data.get('password', '').strip()
        if password:
            customer_service.change_password_as_admin(customer_id, password)
            update_data['password'] = password

        # Update other fields
        for field in ['username', 'email', 'first_name', 'last_name', 'phone_number']:
            if field in data:
                update_data[field] = data[field]

        update_data['is_active'] = data.get('is_active') == 'on'

        success = customer_model.update(customer_id, **update_data)

        if success:
            # Log activity
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=session['admin_id'],
                action='update_customer',
                table_name='customers',
                record_id=customer_id,
                old_values=customer,
                new_values=data
            )

        return success, customer
    
    @staticmethod
    def get_customer_details(customer_id): 
        customer_model = Customer()
        order_model = Order()

        customer = customer_model.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Get customer orders
        customer_orders = [o for o in order_model.get_all() if o.get('customer_id') == customer_id] \
            if hasattr(order_model, 'get_all') else []

        total_spent = sum(float(o.get('total_amount', 0)) for o in customer_orders if o.get('order_status') == 'completed')
        recent_orders = sorted(customer_orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5]

        # Format recent orders
        formatted_recent_orders = [
            {
                'order_id': o['order_id'],
                'order_number': o['order_number'],
                'order_status': o['order_status'],
                'total_amount': float(o['total_amount']),
                'created_at': o['created_at'].isoformat() if o.get('created_at') else None
            } 
            for o in recent_orders
        ]

        customer_data = {
            'customer_id': customer['customer_id'],
            'username': customer['username'],
            'email': customer['email'],
            'first_name': customer['first_name'],
            'last_name': customer['last_name'],
            'phone_number': customer.get('phone_number'),
            'is_active': customer.get('is_active', True),
            'created_at': customer['created_at'].isoformat() if customer.get('created_at') else None,
            'last_login': customer['last_login'].isoformat() if customer.get('last_login') else None,
            'total_orders': len(customer_orders),
            'total_spent': total_spent,
            'recent_orders': formatted_recent_orders
        }

        return customer_data


    @staticmethod
    def change_customer_password(admin_id, customer_id, new_password):
        if not new_password or not new_password.strip():
            raise ValueError("Password is required")

        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Update password
        customer_model.update_password(customer_id, new_password)

        # Log admin activity
        AdminActivityLog().create_log(
            admin_id=admin_id,
            action='change_customer_password',
            table_name='customers',
            record_id=customer_id,
            old_values=None,
            new_values={'action': 'password_changed'}
        )

        return True
 

# ============================================
# ADMIN USER MANAGEMENT (SUPER ADMIN ONLY)
# ============================================
    @staticmethod
    def get_admin_profile(admin_id, current_admin_id, current_role): 
        if current_role != 'super_admin' and admin_id != current_admin_id:
            raise PermissionError("You can only view your own profile.")

        # Fetch admin data
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        if not admin:
            raise ValueError("Admin user not found.")

        return admin

    @staticmethod
    def get_admins_list(filters=None, sort_by='id', sort_order='asc'): 
        filters = filters or {}
        role_filter = filters.get('role', '').strip()
        status_filter = filters.get('status', '').strip()
        search_term = filters.get('search', '').strip().lower()

        admin_model = AdminUser()
        admins = admin_model.get_all()

        # Filter by role
        if role_filter:
            admins = [a for a in admins if a['role'] == role_filter]

        # Filter by status
        if status_filter == 'active':
            admins = [a for a in admins if a.get('is_active', True)]
        elif status_filter == 'inactive':
            admins = [a for a in admins if not a.get('is_active', True)]

        # Filter by search
        if search_term:
            admins = [
                a for a in admins
                if search_term in a['username'].lower()
                   or search_term in a['email'].lower()
                   or search_term in a['first_name'].lower()
                   or search_term in a['last_name'].lower()
            ]

        # Sorting
        reverse = (sort_order == 'desc')
        sort_key_map = {
            'id': lambda a: a['admin_id'],
            'username': lambda a: a['username'].lower(),
            'name': lambda a: (a['first_name'] + a['last_name']).lower(),
            'role': lambda a: a['role'].lower(),
            'created': lambda a: a.get('created_at') or '',
            'last_login': lambda a: a.get('last_login') or ''
        }
        sort_key = sort_key_map.get(sort_by, lambda a: a['admin_id'])
        admins.sort(key=sort_key, reverse=reverse)

        return admins

    @staticmethod
    def get_admin_by_id(admin_id): 
        admin_model = AdminUser()
        return admin_model.get_by_id(admin_id)


    @staticmethod
    def create_admin(username, email, password, first_name='', last_name='',
                     role='admin', is_active=True, created_by=None): 
        admin_model = AdminUser()
        admin_id = admin_model.create(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active,
            created_by=created_by
        )
        return admin_id
    
    @staticmethod
    def update_admin(admin_id, data, updated_by=None): 
        admin_model = AdminUser()
        activity_log_model = AdminActivityLog()

        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, 'Admin not found'

        update_data = {}
        for field in ['email', 'first_name', 'last_name', 'role', 'is_active']:
            if field in data:
                update_data[field] = data[field]

        if update_data:
            admin_model.update(admin_id, **update_data)

            # Log activity
            activity_log_model.create_log(
                admin_id=updated_by or session.get('admin_id'),
                action='update_admin_user',
                table_name='admin_users',
                record_id=admin_id,
                old_values=admin,
                new_values=data
            )

        return True, 'Admin updated successfully'

    @staticmethod
    def update_admin_from_form(admin_id, form_data, current_admin_id=None, current_role=None): 
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, 'Admin user not found'

        # Update full name
        first_name = form_data.get('first_name')
        last_name = form_data.get('last_name')
        if first_name or last_name:
            admin_model.update_full_name(admin_id, first_name=first_name, last_name=last_name)

        # Role and status (super_admin only)
        new_role = form_data.get('role')
        is_active = True if form_data.get('is_active') == "on" else False

        if current_role == 'super_admin' and admin_id != current_admin_id:
            if new_role:
                admin_model.update_role(admin_id, new_role)
            admin_model.update_status(admin_id, is_active)

        # Password
        password = form_data.get('password')
        if password and password.strip() != "":
            admin_model.update_password(admin_id, password)

        return True, 'Admin updated successfully'


    @staticmethod
    def change_password(admin_id, new_password, updated_by=None): 
        admin_model = AdminUser()
        activity_log_model = AdminActivityLog()

        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, "Admin user not found"

        try:
            admin_model.update_password(admin_id, new_password)

            # Log activity
            activity_log_model.create_log(
                admin_id=updated_by or admin_id,
                action='change_admin_password',
                table_name='admin_users',
                record_id=admin_id,
                old_values=None,
                new_values={'action': 'password_changed'}
            )

            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Failed to change password: {str(e)}"

    @staticmethod
    def deactivate_admin(admin_id, performed_by=None): 
        current_admin_id = performed_by or session.get('admin_id')
        if admin_id == current_admin_id:
            return False, "Cannot deactivate your own account"

        admin_model = AdminUser()
        activity_log_model = AdminActivityLog()

        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, "Admin user not found"

        try:
            admin_model.update_status(admin_id, False)
            activity_log_model.create_log(
                admin_id=current_admin_id,
                action='deactivate_admin_user',
                table_name='admin_users',
                record_id=admin_id,
                old_values={'is_active': True},
                new_values={'is_active': False}
            )
            return True, "Admin user deactivated successfully"
        except Exception as e:
            return False, f"Failed to deactivate admin user: {str(e)}"

    @staticmethod
    def activate_admin(admin_id, performed_by=None): 
        current_admin_id = performed_by or session.get('admin_id')

        admin_model = AdminUser()
        activity_log_model = AdminActivityLog()

        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, "Admin user not found"

        try:
            admin_model.update_status(admin_id, True)
            activity_log_model.create_log(
                admin_id=current_admin_id,
                action='activate_admin_user',
                table_name='admin_users',
                record_id=admin_id,
                old_values={'is_active': False},
                new_values={'is_active': True}
            )
            return True, "Admin user activated successfully"
        except Exception as e:
            return False, f"Failed to activate admin user: {str(e)}"

    @staticmethod
    def delete_admin(admin_id, performed_by=None): 
        current_admin_id = performed_by or session.get('admin_id')

        if current_admin_id == admin_id:
            return False, "You cannot delete your own account"

        admin_model = AdminUser()
        activity_log_model = AdminActivityLog()

        admin = admin_model.get_by_id(admin_id)
        if not admin:
            return False, "Admin user not found"

        try:
            # Log deletion
            activity_log_model.create_log(
                admin_id=current_admin_id,
                action='delete_admin_user',
                table_name='admin_users',
                record_id=admin_id,
                old_values={'username': admin['username'], 'email': admin['email']},
                new_values=None
            )

            admin_model.delete(admin_id)
            return True, "Admin user deleted successfully"

        except Exception as e:
            return False, f"Failed to delete admin user: {str(e)}"