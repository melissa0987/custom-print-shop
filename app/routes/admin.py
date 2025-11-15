"""
app/routes/admin.py
Admin Routes
Handles admin panel operations (orders, products, customers, reports) 
"""

from flask import Blueprint, current_app, flash, redirect, request, jsonify, session, url_for, render_template

from app.models import (
    Order, OrderItem, OrderStatusHistory, Product, Category,
    Customer, AdminUser, AdminActivityLog
)
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.utils import admin_required, permission_required
from datetime import datetime

from app.utils.decorators import validate_order_access
from app.utils.helpers import DateHelper, PaginationHelper, PriceHelper, StringHelper
from app.utils.image_helpers import ImageHelper
import os
from werkzeug.utils import secure_filename 

 
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================
# ADMIN LOGIN
# ============================================ 
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page + login handler"""

    # If already logged in, redirect to dashboard
    if session.get('admin_id'):
        return redirect(url_for('admin.get_dashboard'))
      
    if request.method == 'GET':
        return render_template('admin/admin_login.html')

    # Get form data
    data = request.get_json(silent=True) or request.form.to_dict()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        error_msg = 'Email and password are required'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')

    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_email(email.lower())

        print("DEBUG: admin fetched from DB:", admin)
        print("DEBUG: admin type:", type(admin))

        # Check if admin exists
        if not admin:
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Verify password using the AdminUser static method
        if not AdminUser.verify_password(admin, password):
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Check if active
        if not admin.get('is_active', True):
            error_msg = 'Admin account is inactive. Please contact support.'
            if request.is_json:
                return jsonify({'error': error_msg}), 403
            flash(error_msg, 'danger')
            return render_template('admin/admin_login.html')

        # Update last login
        admin_model.update_last_login(admin['admin_id'])

        # Store admin info in session
        session['admin_id'] = admin['admin_id']
        session['admin_username'] = admin['username']
        session['admin_role'] = admin.get('role', 'staff')
        session['admin_email'] = admin['email']
        session['admin_first_name'] = admin.get('first_name', '')
        
        # Get permissions for this admin
        permissions = admin_model.get_permissions(admin['admin_id'])
        session['permissions'] = permissions
        session.permanent = True

        # Log activity
        try:
            activity_log_model = AdminActivityLog()
            activity_log_model.create_log(
                admin_id=admin['admin_id'],
                action='login',
                table_name='admin_users',
                record_id=admin['admin_id'],
                old_values=None,
                new_values={'status': 'success', 'timestamp': datetime.now().isoformat()}
            )
        except Exception as log_error:
            print(f"Warning: Failed to log admin activity: {log_error}")

        flash(f'Welcome back, {admin.get("first_name", admin["username"])}!', 'success')
        
        # Handle redirect
        next_page = request.args.get('next') or request.form.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin.get_dashboard'))

    except Exception as e:
        import traceback
        error_msg = f'Login failed: {str(e)}'
        print("DEBUG: Full error traceback:")
        print(traceback.format_exc())
        
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'danger')
        return render_template('admin/admin_login.html')


# ============================================
# DASHBOARD - HTML PAGE
# ============================================ 
@admin_bp.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('main.homepage'))



@admin_bp.route('/dashboard', methods=['GET'])
@permission_required('view_dashboard')
def get_dashboard():
    """Render admin dashboard with stats"""
    try:
        from app.models import Order, Customer, Product

        order_model = Order()
        customer_model = Customer()
        product_model = Product()

        # Orders
        all_orders = order_model.get_all()
        total_orders = len(all_orders)
        pending_orders = sum(1 for o in all_orders if o['order_status'] == 'pending')
        processing_orders = sum(1 for o in all_orders if o['order_status'] == 'processing')

        # Revenue
        total_revenue = sum(o['total_amount'] for o in all_orders)
        month_revenue = sum(
            o['total_amount'] for o in all_orders
            if o['created_at'].month == datetime.now().month
        )

        # Customers
        all_customers = customer_model.get_all()
        total_customers = len(all_customers)
        active_customers = sum(1 for c in all_customers if c.get('is_active'))

        # Products
        all_products = product_model.get_all(active_only=False)
        total_products = len(all_products)
        active_products = sum(1 for p in all_products if p.get('is_active'))
        recent_orders = sorted(
                all_orders,
                key=lambda o: o['created_at'],
                reverse=True
            )[:5]

        return render_template(
            'admin/admin_dashboard.html',
            stats={
                'orders': {
                    'total': total_orders,
                    'pending': pending_orders,
                    'processing': processing_orders
                },
                'revenue': {
                    'total': total_revenue,
                    'month': month_revenue
                },
                'customers': {
                    'total': total_customers,
                    'active': active_customers
                },
                'products': {
                    'total': total_products,
                    'active': active_products
                }
            }, recent_orders=recent_orders
        )

    except Exception as e:
        flash(f"Failed to load dashboard: {str(e)}", "danger")
        return render_template('admin/admin_dashboard.html', stats=None)


# ============================================
# ORDER MANAGEMENT
# ============================================
@admin_bp.route('/orders', methods=['GET'])
@permission_required('view_orders')
def get_orders():
    """Render orders management page with data passed via Jinja"""
    status_filter = request.args.get('status')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        order_model = Order()
        customer_model = Customer()
        
        # Get all orders
        all_orders = order_model.get_all() if hasattr(order_model, 'get_all') else []
        
        # Apply status filter
        if status_filter:
            all_orders = [o for o in all_orders if o.get('order_status') == status_filter]
        
        # Format orders with customer info
        formatted_orders = []
        for order in all_orders:
            customer_username = 'Guest'
            customer_email = order.get('contact_email')
            
            if order.get('customer_id'):
                customer = customer_model.get_by_id(order['customer_id'])
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
        total_orders = len(formatted_orders)
        offset = (page - 1) * per_page
        paginated_orders = formatted_orders[offset:offset + per_page]
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_orders': total_orders,
            'total_pages': max(1, (total_orders + per_page - 1) // per_page),
            'has_next': page * per_page < total_orders,
            'has_prev': page > 1
        }
        
        return render_template(
            'admin/admin_orders.html',
            orders=paginated_orders,
            pagination=pagination
        )
            
    except Exception as e:
        flash(f'Failed to load orders: {str(e)}', 'danger')
        return render_template('admin/admin_orders.html', orders=[], pagination=None)

 
@admin_bp.route('/orders/<int:order_id>', methods=['GET'])
@permission_required('view_orders')
def get_order_details(order_id):
    """Get order details - returns HTML page or JSON for AJAX"""
    try:
        # Admin can view any order; bypass ownership checks
        order_model = Order()
        order_item_model = OrderItem()
        product_model = Product()
        category_model = Category()
        order_status_history_model = OrderStatusHistory()

        order = order_model.get_by_id(order_id)
        
        # Store raw datetime objects for later formatting
        raw_created_at = order.get('created_at')
        raw_updated_at = order.get('updated_at')

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
            'created_at': raw_created_at,  # Keep as datetime object initially
            'updated_at': raw_updated_at   # Keep as datetime object initially
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

        # Add items
        items = []
        order_items = order_item_model.get_by_order(order_id)
        for oi in order_items:
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
                    'category_name': category['category_name']
                },
                'quantity': oi['quantity'],
                'unit_price': float(oi['unit_price']),
                'subtotal': float(oi['subtotal']),
                'design_file_url': oi.get('design_file_url'),
                'customizations': customizations
            })
        order_data['items'] = items

        # Add status history
        history = []
        status_records = order_status_history_model.get_by_order(order_id) or []
        for h in status_records:
            history.append({
                'status': h.get('status'),
                'changed_at': h['changed_at'].isoformat() if h.get('changed_at') else None,
                'changed_by': order_status_history_model.get_changed_by_name(h),
                'notes': h.get('notes')
            })
        order_data['status_history'] = history

        # Root-level customer info for template
        if isinstance(order_data.get('customer'), dict):
            order_data['customer_name'] = order_data['customer'].get('full_name', 'Unknown')
            order_data['customer_email'] = order_data['customer'].get('email', 'N/A')
        else:
            order_data['customer_name'] = 'Guest'
            order_data['customer_email'] = order_data.get('contact_email', 'N/A')

        # Format dates differently based on request type
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # For JSON/AJAX: use ISO format strings
            if raw_created_at:
                order_data['created_at'] = raw_created_at.isoformat() if isinstance(raw_created_at, datetime) else raw_created_at
            if raw_updated_at:
                order_data['updated_at'] = raw_updated_at.isoformat() if isinstance(raw_updated_at, datetime) else raw_updated_at
        else:
            # For HTML: use formatted strings
            if raw_created_at:
                order_data['created_at'] = DateHelper.format_datetime(raw_created_at)
            if raw_updated_at:
                order_data['updated_at'] = DateHelper.format_datetime(raw_updated_at)

        # Fallback images for products
        for item in order_data.get("items", []):
            pname = item["product"]["product_name"].lower()
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
            if not item["product"].get("image_url"):
                item["product"]["image_url"] = img

        # JSON response for AJAX
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'order': order_data}), 200

        # Render HTML
        return render_template('admin/admin_order_detail.html', order=order_data)

    except Exception as e:
        import traceback
        print(f"Error in get_order_details: {str(e)}")
        print(traceback.format_exc())
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': f'Failed to get order details: {str(e)}'}), 500
        flash(f'Failed to get order details: {str(e)}', 'error')
        return redirect(url_for('admin.get_orders'))     


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@permission_required('update_order_status')
def update_order_status(order_id):
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')

    if not new_status or new_status not in ['pending', 'processing', 'completed', 'cancelled']:
        flash('Invalid status', 'error')
        return redirect(url_for('admin.get_order_details', order_id=order_id))

    order_model = Order()
    order = order_model.get_by_id(order_id)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('admin.get_orders'))

    old_status = order['order_status']
    order_model.update_status(order_id, new_status, updated_by=session['admin_id'])

    # Log history
    OrderStatusHistory().create(
        order_id=order_id,
        status=new_status,
        changed_by=session['admin_id'],
        notes=notes
    )

    AdminActivityLog().create_log(
        admin_id=session['admin_id'],
        action='update_order_status',
        table_name='orders',
        record_id=order_id,
        old_values={'order_status': old_status},
        new_values={'order_status': new_status, 'notes': notes}
    )

    flash(f'Status updated to {new_status}', 'success')
    return redirect(url_for('admin.get_order_details', order_id=order_id))

# ============================================
# PRODUCT MANAGEMENT
# ============================================
@admin_bp.route('/products', methods=['GET'])
@permission_required('view_products')
def get_products_admin():
    wants_json = request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']

    category_id = request.args.get('category_id', type=int)
    search_term = request.args.get('search', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

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
            products = [p for p in products if s in p.get('product_name', '').lower() or s in p.get('description', '').lower()]

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

        pagination_data = {
            'page': paginated['page'],
            'per_page': paginated['per_page'],
            'total_items': paginated['total_items'],
            'total_pages': max(1, paginated['total_pages']),
            'has_next': paginated['page'] < paginated['total_pages'],
            'has_prev': paginated['page'] > 1
        }

        # Get all categories for filter dropdown
        categories = category_model.get_all()
        categories_for_template = [{'category_id': c['category_id'], 'category_name': c['category_name']} for c in categories]

        if wants_json:
            return jsonify({'products': formatted_products, 'pagination': pagination_data}), 200

        return render_template('admin/admin_products.html',
                               products=formatted_products,
                               pagination=pagination_data,
                               categories=categories_for_template,
                               current_category=category_id,
                               search_term=search_term,
                               sort_by=sort_by,
                               sort_order=sort_order)

    except Exception as e:
        flash(f'Failed to load products: {str(e)}', 'danger')
        return redirect(url_for('admin.get_dashboard'))

 
def get_products_data():
    """API endpoint to get all products"""
    category_id = request.args.get('category_id', type=int)
    is_active_str = request.args.get('is_active')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        product_model = Product()
        category_model = Category()
        
        # Get products
        if is_active_str and is_active_str.lower() == 'false':
            products = product_model.get_all(active_only=False)
        else:
            products = product_model.get_all(active_only=True)
        
        # Filter by category
        if category_id:
            products = [p for p in products if p.get('category_id') == category_id]
        
        # Sort by product name
        products.sort(key=lambda x: x.get('product_name', '').lower())
        
        # Get total count
        total_products = len(products)
        
        # Pagination
        offset = (page - 1) * per_page
        products = products[offset:offset + per_page]
        
        # Format results
        result = []
        for p in products:
            category = category_model.get_by_id(p['category_id'])
            result.append({
                'product_id': p['product_id'],
                'category_id': p['category_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'category_name': category['category_name'] if category else 'Unknown',
                'is_active': p.get('is_active'),
                'times_ordered': product_model.get_total_orders(p['product_id']),
                'total_revenue': product_model.get_total_revenue(p['product_id'])
            })
        
        return jsonify({
            'products': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_products': total_products
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500


@admin_bp.route('/products/create', methods=['GET', 'POST'])
@permission_required('manage_products')
def create_product():
    """Create new product with image"""
    if request.method == 'GET':
        try:
            categories = Category().get_all()
            return render_template('admin/admin_product_form.html', categories=categories, action='create')
        except Exception as e:
            flash(f'Failed to load form: {str(e)}', 'danger')
            return redirect(url_for('admin.get_products_admin'))
    
    # POST
    data = request.form.to_dict()
    file = request.files.get('product_image')

    required_fields = ['product_name', 'category_id', 'base_price']
    for field in required_fields:
        if not data.get(field):
            flash(f'{field} is required', 'danger')
            return redirect(url_for('admin.create_product'))
    
    try:
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

        if file and ImageHelper.validate_image_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            
            # Main product image
            product_filename = f"{secure_filename(data['product_name'])}.{ext}"
            product_path = os.path.join(current_app.root_path, ImageHelper.PRODUCT_IMAGES_DIR, product_filename)
            file.save(product_path)

            # Mockup image
            mockup_filename = f"product_{product_id}_mockup.{ext}"
            mockup_path = os.path.join(current_app.root_path, ImageHelper.MOCKUPS_DIR, mockup_filename)
            file.seek(0)
            file.save(mockup_path)

            # Update product record with main image URL
            Product().update(product_id, image_url=f"images/products/{product_filename}")

        flash('Product created successfully', 'success')
        return redirect(url_for('admin.get_products_admin'))
    
    except Exception as e:
        flash(f'Failed to create product: {str(e)}', 'danger')
        return redirect(url_for('admin.create_product'))

@admin_bp.route('/products/<int:product_id>', methods=['GET'])
@permission_required('view_products')
def get_product_detail(product_id):
    """
    Display details for a single product in the admin panel.
    """
    try:
        product_model = Product()
        category_model = Category()

        # Fetch the product by ID (including inactive for admin)
        product = product_model.get_by_id(product_id)
        if not product:
            flash(f'Product with ID {product_id} not found.', 'warning')
            return redirect(url_for('admin.get_products_admin'))

        # Get category info
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
        categories = Category().get_all()

        return render_template(
            'admin/admin_product_detail.html',
            product=formatted_product,
            categories=categories
        )

    except Exception as e:
        flash(f'Failed to load product details: {str(e)}', 'danger')
        return redirect(url_for('admin.get_products_admin'))


@admin_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@permission_required('manage_products')
def toggle_product_status(product_id):
    """Toggle product active status (deactivate/activate)"""
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin.get_products_admin'))
        
        new_status = not product.get('is_active', True)
        
        success = product_model.update(
            product_id,
            is_active=new_status,
            updated_by=session.get('admin_id')
        )
        
        if not success:
            flash('Failed to toggle product status', 'danger')
            return redirect(url_for('admin.get_products_admin'))
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='toggle_product_status',
            table_name='products',
            record_id=product_id,
            old_values={'is_active': product.get('is_active')},
            new_values={'is_active': new_status}
        )
        
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Product {status_text} successfully', 'success')
        return redirect(url_for('admin.get_products_admin'))
            
    except Exception as e:
        flash(f'Failed to toggle product status: {str(e)}', 'danger')
        return redirect(url_for('admin.get_products_admin'))
    


@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@permission_required('manage_products')
def delete_product(product_id):
    """Delete product: soft delete if there are related orders, else hard delete"""
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin.get_products_admin'))
        
        # Check if product has orders
        total_orders = product_model.get_total_orders(product_id)
        
        if total_orders > 0:
            # Soft delete: deactivate product
            success = product_model.update(
                product_id,
                is_active=False,
                updated_by=session.get('admin_id')
            )
            if success:
                flash('Product has existing orders, so it was deactivated.', 'info')
            else:
                flash('Failed to deactivate product.', 'danger')
        else:
            # Hard delete: no related orders
            success = product_model.delete(product_id)
            if success:
                flash('Product deleted successfully.', 'success')
            else:
                flash('Failed to delete product.', 'danger')
        
        return redirect(url_for('admin.get_products_admin'))
            
    except Exception as e:
        flash(f'Failed to delete product: {str(e)}', 'danger')
        return redirect(url_for('admin.get_products_admin'))

@admin_bp.route('/products/<int:product_id>', methods=['POST'])
@permission_required('manage_products')
def update_product(product_id):
    """Update existing product"""
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('admin.get_products_admin'))

        data = request.form.to_dict()
        file = request.files.get('product_image')

        # Update product
        product_model.update(
            product_id,
            product_name=data.get('product_name'),
            category_id=int(data.get('category_id')),
            base_price=float(data.get('base_price')),
            description=data.get('description'),
            is_active=data.get('is_active') == 'on',
            updated_by=session.get('admin_id')
        )

        # Update image if uploaded
        if file and ImageHelper.validate_image_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{secure_filename(data['product_name'])}.{ext}"
            path = os.path.join(current_app.root_path, ImageHelper.PRODUCT_IMAGES_DIR, filename)
            file.save(path)
            product_model.update(product_id, image_url=f"images/products/{filename}")

        flash('Product updated successfully', 'success')
        return redirect(url_for('admin.get_product_detail', product_id=product_id))

    except Exception as e:
        flash(f'Failed to update product: {str(e)}', 'danger')
        return redirect(url_for('admin.get_products_admin'))


# ============================================
# CATEGORY MANAGEMENT
# ============================================
@admin_bp.route('/categories', methods=['GET'])
@permission_required('view_categories')
def get_categories_admin():
    """Render categories management page"""
    try:
        category_model = Category()
        categories = category_model.get_all()
        
        formatted_categories = []
        for c in categories:
            formatted_categories.append({
                'category_id': c['category_id'],
                'category_name': c['category_name'],
                'description': c.get('description'),
                'is_active': c.get('is_active'),
                'display_order': c.get('display_order', 0),
                'product_count': len(c.get('products', [])),
                'created_at': c['created_at'].isoformat() if c.get('created_at') else None,
                'updated_at': c['updated_at'].isoformat() if c.get('updated_at') else None
            })
        
        # Sort by display_order
        formatted_categories.sort(key=lambda x: x['display_order'])
        
        return render_template('admin/admin_categories.html', 
                             categories=formatted_categories)
            
    except Exception as e:
        flash(f'Failed to load categories: {str(e)}', 'danger')
        return redirect(url_for('admin.get_dashboard'))
    

@admin_bp.route('/categories', methods=['GET'])
@permission_required('view_categories')
def get_categories():
    """Render categories management page or return JSON for AJAX"""
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_categories_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admin_categories.html')


def get_categories_data():
    """API endpoint to get all categories"""
    try:
        category_model = Category()
        product_model = Product()
        
        categories = category_model.get_all()
        
        # Add product count to each category
        result = []
        for cat in categories:
            products = product_model.get_by_category(cat['category_id']) if hasattr(product_model, 'get_by_category') else []
            result.append({
                'category_id': cat['category_id'],
                'category_name': cat['category_name'],
                'description': cat.get('description'),
                'display_order': cat.get('display_order', 0),
                'is_active': cat.get('is_active', True),
                'created_at': cat['created_at'].isoformat() if cat.get('created_at') else None,
                'product_count': len(products)
            })
        
        return jsonify({'categories': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get categories: {str(e)}'}), 500

@admin_bp.route('/categories/create', methods=['GET', 'POST'])
@permission_required('manage_categories')
def create_category():
    """Create new category"""
    if request.method == 'GET':
        return render_template('admin/admin_category_form.html', action='create')
    
    # POST - handle form submission
    data = request.form.to_dict()
    
    if 'category_name' not in data or not data['category_name']:
        flash('category_name is required', 'danger')
        return redirect(url_for('admin.create_category'))
    
    try:
        category_model = Category()
        
        category_id = category_model.create(
            category_name=data['category_name'],
            description=data.get('description'),
            is_active=data.get('is_active') == 'on',
            display_order=int(data.get('display_order', 0)),
            created_by=session.get('admin_id')
        )
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='create_category',
            table_name='categories',
            record_id=category_id,
            old_values=None,
            new_values=data
        )
        
        flash('Category created successfully', 'success')
        return redirect(url_for('admin.get_categories_admin'))
            
    except Exception as e:
        flash(f'Failed to create category: {str(e)}', 'danger')
        return redirect(url_for('admin.create_category')) 

@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_categories')
def edit_category(category_id):
    """Edit category"""
    category_model = Category()
    
    if request.method == 'GET':
        # Render edit form
        try:
            category = category_model.get_by_id(category_id)
            if not category:
                flash('Category not found', 'danger')
                return redirect(url_for('admin.get_categories_admin'))
            
            return render_template('admin/admin_category_form.html', 
                                 category=category,
                                 action='edit')
        except Exception as e:
            flash(f'Failed to load category: {str(e)}', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
    
    # POST - handle form submission
    data = request.form.to_dict()
    
    try:
        category = category_model.get_by_id(category_id)
        if not category:
            flash('Category not found', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        # Update category
        update_data = {}
        if 'category_name' in data:
            update_data['category_name'] = data['category_name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'display_order' in data:
            update_data['display_order'] = int(data['display_order'])
        
        update_data['is_active'] = data.get('is_active') == 'on'
        update_data['updated_by'] = session.get('admin_id')
        
        success = category_model.update(category_id, **update_data)
        
        if not success:
            flash('Failed to update category', 'danger')
            return redirect(url_for('admin.edit_category', category_id=category_id))
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_category',
            table_name='categories',
            record_id=category_id,
            old_values=category,
            new_values=data
        )
        
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin.get_categories_admin'))
            
    except Exception as e:
        flash(f'Failed to update category: {str(e)}', 'danger')
        return redirect(url_for('admin.edit_category', category_id=category_id))


@admin_bp.route('/categories/<int:category_id>/toggle', methods=['POST'])
@permission_required('manage_categories')
def toggle_category_status(category_id):
    """Toggle category active status"""
    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)
        
        if not category:
            flash('Category not found', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        new_status = not category.get('is_active', True)
        
        success = category_model.update(
            category_id,
            is_active=new_status,
            updated_by=session.get('admin_id')
        )
        
        if not success:
            flash('Failed to toggle category status', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='toggle_category_status',
            table_name='categories',
            record_id=category_id,
            old_values={'is_active': category.get('is_active')},
            new_values={'is_active': new_status}
        )
        
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Category {status_text} successfully', 'success')
        return redirect(url_for('admin.get_categories_admin'))
            
    except Exception as e:
        flash(f'Failed to toggle category status: {str(e)}', 'danger')
        return redirect(url_for('admin.get_categories_admin'))
    

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@permission_required('manage_categories')
def delete_category(category_id):
    """Delete category"""
    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)
        
        if not category:
            flash('Category not found', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        # Check if category has products
        if len(category.get('products', [])) > 0:
            flash('Cannot delete category with products. Remove or reassign products first.', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        # Log activity before deletion
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='delete_category',
            table_name='categories',
            record_id=category_id,
            old_values=category,
            new_values=None
        )
        
        success = category_model.delete(category_id)
        
        if not success:
            flash('Failed to delete category', 'danger')
            return redirect(url_for('admin.get_categories_admin'))
        
        flash('Category deleted successfully', 'success')
        return redirect(url_for('admin.get_categories_admin'))
            
    except Exception as e:
        flash(f'Failed to delete category: {str(e)}', 'danger')
        return redirect(url_for('admin.get_categories_admin'))  


# ============================================
# CUSTOMER MANAGEMENT
# ============================================
@admin_bp.route('/customers', methods=['GET'])
@permission_required('view_customers')
def get_customers_admin():
    """Render customers management page with totals and optional filters/sorting"""
    status_filter = request.args.get('status')  # 'active', 'inactive', or None
    search_term = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')

    try:
        customer_model = Customer()
        order_model = Order()

        customers = customer_model.get_all()

        # Compute totals for each customer
        formatted_customers = []
        for c in customers:
            orders = order_model.get_by_customer(c['customer_id'])
            total_orders = len(orders)
            total_spent = sum(order['total_amount'] for order in orders)
            formatted_customers.append({
                'customer_id': c['customer_id'],
                'username': c['username'],
                'email': c['email'],
                'first_name': c.get('first_name', ''),
                'last_name': c.get('last_name', ''),
                'phone_number': c.get('phone_number', ''),
                'is_active': c.get('is_active', True),
                'created_at': c['created_at'].isoformat() if c.get('created_at') else None,
                'last_login': c['last_login'].isoformat() if c.get('last_login') else None,
                'total_orders': total_orders,
                'total_spent': total_spent
            })

        # Apply status filter
        if status_filter == 'active':
            formatted_customers = [c for c in formatted_customers if c['is_active']]
        elif status_filter == 'inactive':
            formatted_customers = [c for c in formatted_customers if not c['is_active']]

        # Apply search filter
        if search_term:
            formatted_customers = [
                c for c in formatted_customers
                if search_term.lower() in (c['username'] + c['first_name'] + c['last_name'] + c['email']).lower()
            ]

        # Sort
        reverse = (sort_order == 'desc')
        sort_key_map = {
            'id': lambda x: x['customer_id'],
            'username': lambda x: x['username'].lower(),
            'name': lambda x: (x['first_name'] + x['last_name']).lower(),
            'orders': lambda x: x['total_orders'],
            'spent': lambda x: x['total_spent'],
            'joined': lambda x: x['created_at'] or ''
        }
        if sort_by in sort_key_map:
            formatted_customers.sort(key=sort_key_map[sort_by], reverse=reverse)
        else:
            # default to ID sort
            formatted_customers.sort(key=lambda x: x['customer_id'])

        return render_template(
            'admin/admin_customers.html',
            customers=formatted_customers,
            status=status_filter,
            search=search_term,
            sort_by=sort_by,
            sort_order=sort_order
        )

    except Exception as e:
        flash(f'Failed to load customers: {str(e)}', 'danger')
        return redirect(url_for('admin.get_dashboard'))


@admin_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@permission_required('manage_customers')
def edit_customer(customer_id):
    """Edit customer"""
    customer_model = Customer()
    customer_service = CustomerService()
    
    if request.method == 'GET':
        try:
            customer = customer_model.get_by_id(customer_id)
            if not customer:
                flash('Customer not found', 'danger')
                return redirect(url_for('admin.get_customers_admin'))

            # 🔥 Get customer order list
            success, customer_orders = OrderService.get_order_list_by_customer_id(customer_id)
            if not success:
                customer_orders = []

            return render_template(
                'admin/admin_customer_form.html',
                customer=customer,
                customer_orders=customer_orders,
                action='edit'
            )

        except Exception as e:
            flash(f'Failed to load customer: {str(e)}', 'danger')
            return redirect(url_for('admin.get_customers_admin'))
    

    if request.method == 'POST': 
    # POST - handle form submission
        data = request.form.to_dict()
        
        try:
            customer = customer_model.get_by_id(customer_id)
            if not customer:
                flash('Customer not found', 'danger')
                return redirect(url_for('admin.get_customers_admin'))
            
            
            # Update customer
            update_data = {}
            # Only update password if provided
            if 'password' in data and data['password'].strip():
                update_data['password'] = data['password'].strip()
                customer_service.change_password_as_admin(customer_id, update_data['password'])

            for field in ['username', 'email', 'first_name', 'last_name', 'phone_number']:
                if field in data:
                    update_data[field] = data[field]
            
            update_data['is_active'] = data.get('is_active') == 'on'
            
            success = customer_model.update(customer_id, **update_data)
            
            if not success:
                flash('Failed to update customer', 'danger')
                return redirect(url_for('admin.edit_customer', customer_id=customer_id))
            
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
            
            flash('Customer updated successfully', 'success')
            return redirect(url_for('admin.edit_customer', customer_id=customer_id))
                
        except Exception as e:
            flash(f'Failed to update customer: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_customer', customer_id=customer_id))


@admin_bp.route('/customers/<int:customer_id>/toggle', methods=['POST'])
@permission_required('manage_customers')
def toggle_customer_status(customer_id):
    """Toggle customer active status (deactivate/activate)"""
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            flash('Customer not found', 'danger')
            return redirect(url_for('admin.get_customers_admin'))
        
        new_status = not customer.get('is_active', True)
        
        success = customer_model.update(customer_id, is_active=new_status)
        
        if not success:
            flash('Failed to toggle customer status', 'danger')
            return redirect(url_for('admin.get_customers_admin'))
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='toggle_customer_status',
            table_name='customers',
            record_id=customer_id,
            old_values={'is_active': customer.get('is_active')},
            new_values={'is_active': new_status}
        )
        
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Customer {status_text} successfully', 'success')
        return redirect(url_for('admin.get_customers_admin'))
            
    except Exception as e:
        flash(f'Failed to toggle customer status: {str(e)}', 'danger')
        return redirect(url_for('admin.get_customers_admin'))


def get_customers_data():
    """API endpoint to get all customers"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    try:
        customer_model = Customer()
        order_model = Order()
        
        # Get all customers
        all_customers = customer_model.get_all() if hasattr(customer_model, 'get_all') else []
        
        # Add order statistics
        result = []
        for customer in all_customers:
            customer_orders = [o for o in order_model.get_all() if o.get('customer_id') == customer['customer_id']] if hasattr(order_model, 'get_all') else []
            total_spent = sum(float(o.get('total_amount', 0)) for o in customer_orders if o.get('order_status') == 'completed')
            
            result.append({
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
                'total_spent': total_spent
            })
        
        # Pagination
        total_customers = len(result)
        offset = (page - 1) * per_page
        paginated_customers = result[offset:offset + per_page]
        
        return jsonify({
            'customers': paginated_customers,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_customers': total_customers
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customers: {str(e)}'}), 500

@admin_bp.route('/customers/<int:customer_id>', methods=['GET'])
@permission_required('view_customers')
def get_customer_details(customer_id):
    """Get customer details"""
    try:
        customer_model = Customer()
        order_model = Order()
        
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer orders
        customer_orders = [o for o in order_model.get_all() if o.get('customer_id') == customer_id] if hasattr(order_model, 'get_all') else []
        total_spent = sum(float(o.get('total_amount', 0)) for o in customer_orders if o.get('order_status') == 'completed')
        
        # Get recent orders
        recent_orders = sorted(customer_orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        return jsonify({
            'customer': {
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
                'recent_orders': [
                    {
                        'order_id': o['order_id'],
                        'order_number': o['order_number'],
                        'order_status': o['order_status'],
                        'total_amount': float(o['total_amount']),
                        'created_at': o['created_at'].isoformat() if o.get('created_at') else None
                    }
                    for o in recent_orders
                ]
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get customer details: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>/password', methods=['PUT'])
@permission_required('view_customers')
def change_customer_password(customer_id):
    """Change customer password"""
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400
    
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        customer_model.update_password(customer_id, new_password)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='change_customer_password',
            table_name='customers',
            record_id=customer_id,
            old_values=None,
            new_values={'action': 'password_changed'}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


@admin_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@permission_required('manage_customers')
def delete_customer(customer_id):
    """Delete customer"""
    try:
        customer_model = Customer()
        customer = customer_model.get_by_id(customer_id)
        
        if not customer:
            flash('Customer not found', 'danger')
            return redirect(url_for('admin.get_customers_admin'))
        
        # Log activity before deletion
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='delete_customer',
            table_name='customers',
            record_id=customer_id,
            old_values={'username': customer['username'], 'email': customer['email']},
            new_values=None
        )
        
        success = customer_model.delete(customer_id)
        
        if not success:
            flash('Failed to delete customer', 'danger')
            return redirect(url_for('admin.get_customers_admin'))
        
        flash('Customer deleted successfully', 'success')
        return redirect(url_for('admin.get_customers_admin'))
            
    except Exception as e:
        flash(f'Failed to delete customer: {str(e)}', 'danger')
        return redirect(url_for('admin.get_customers_admin'))
        
         
# ============================================
# ADMIN USER MANAGEMENT (SUPER ADMIN ONLY)
# ============================================

@admin_bp.route('/admins', methods=['GET'])
@admin_required
def get_admins():
    """Render admin users management page or return JSON for AJAX"""
    # Check if user is super admin
    if session.get('admin_role') != 'super_admin':
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Only super admin can access this page'}), 403
        flash('Only super admin can access this page', 'error')
        return redirect(url_for('admin.get_dashboard'))
    
    # If it's an AJAX request, return JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_admins_data()
    
    # Otherwise render the HTML page
    return render_template('admin/admins.html')


def get_admins_data():
    """API endpoint to get all admin users"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    
    try:
        admin_model = AdminUser()
        
        # Get all admins
        all_admins = admin_model.get_all()
        
        # Format admins
        result = []
        for admin in all_admins:
            result.append({
                'admin_id': admin['admin_id'],
                'username': admin['username'],
                'email': admin['email'],
                'first_name': admin['first_name'],
                'last_name': admin['last_name'],
                'role': admin['role'],
                'is_active': admin.get('is_active', True),
                'created_at': admin['created_at'].isoformat() if admin.get('created_at') else None,
                'last_login': admin['last_login'].isoformat() if admin.get('last_login') else None
            })
        
        return jsonify({'admins': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get admin users: {str(e)}'}), 500


@admin_bp.route('/admins', methods=['POST'])
@admin_required
def add_admin():
    """Add new admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can create admin users'}), 403
    
    data = request.get_json()
    
    try:
        admin_model = AdminUser()
        
        admin_id = admin_model.create(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            is_active=data.get('is_active', True),
            created_by=session['admin_id']
        )
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='create_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values=None,
            new_values={'username': data['username'], 'role': data['role']}
        )
        
        return jsonify({
            'message': 'Admin user created successfully',
            'admin_id': admin_id
        }), 201
            
    except Exception as e:
        return jsonify({'error': f'Failed to create admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@admin_required
def update_admin(admin_id):
    """Update admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can update admin users'}), 403
    
    data = request.get_json()
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        # Update fields (excluding password which has separate endpoint)
        update_data = {}
        if 'email' in data:
            update_data['email'] = data['email']
        if 'first_name' in data:
            update_data['first_name'] = data['first_name']
        if 'last_name' in data:
            update_data['last_name'] = data['last_name']
        if 'role' in data:
            update_data['role'] = data['role']
        if 'is_active' in data:
            update_data['is_active'] = data['is_active']
        
        # Update admin - you'll need to implement this method in AdminUser model
        for key, value in update_data.items():
            # This is a simplified version - implement proper update method in model
            pass
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='update_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'role': admin['role']},
            new_values=data
        )
        
        return jsonify({'message': 'Admin user updated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to update admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/password', methods=['PUT'])
@admin_required
def change_admin_password(admin_id):
    """Change admin password (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can change admin passwords'}), 403
    
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_password(admin_id, new_password)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='change_admin_password',
            table_name='admin_users',
            record_id=admin_id,
            old_values=None,
            new_values={'action': 'password_changed'}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/deactivate', methods=['PUT'])
@admin_required
def deactivate_admin(admin_id):
    """Deactivate admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can deactivate admin users'}), 403
    
    # Cannot deactivate yourself
    if admin_id == session.get('admin_id'):
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_status(admin_id, False)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='deactivate_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'is_active': True},
            new_values={'is_active': False}
        )
        
        return jsonify({'message': 'Admin user deactivated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to deactivate admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>/activate', methods=['PUT'])
@admin_required
def activate_admin(admin_id):
    """Activate admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can activate admin users'}), 403
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        admin_model.update_status(admin_id, True)
        
        # Log activity
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='activate_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'is_active': False},
            new_values={'is_active': True}
        )
        
        return jsonify({'message': 'Admin user activated successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to activate admin user: {str(e)}'}), 500


@admin_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@admin_required
def delete_admin(admin_id):
    """Delete admin user (super admin only)"""
    if session.get('admin_role') != 'super_admin':
        return jsonify({'error': 'Only super admin can delete admin users'}), 403
    
    # Cannot delete yourself
    if admin_id == session.get('admin_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    try:
        admin_model = AdminUser()
        admin = admin_model.get_by_id(admin_id)
        
        if not admin:
            return jsonify({'error': 'Admin user not found'}), 404
        
        # Log activity before deletion
        activity_log_model = AdminActivityLog()
        activity_log_model.create_log(
            admin_id=session['admin_id'],
            action='delete_admin_user',
            table_name='admin_users',
            record_id=admin_id,
            old_values={'username': admin['username'], 'role': admin['role']},
            new_values=None
        )
        
        admin_model.delete(admin_id)
        
        return jsonify({'message': 'Admin user deleted successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete admin user: {str(e)}'}), 500


# ============================================
# REPORTS
# ============================================

@admin_bp.route('/reports', methods=['GET'])
@permission_required('view_reports')
def get_reports():
    """Render reports page"""
    return render_template('admin/admin_reports.html')


@admin_bp.route('/reports/sales', methods=['GET'])
@permission_required('view_reports')
def get_sales_report():
    """Get sales report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')
    
    try:
        # TODO: Implement sales report logic
        return jsonify({
            'sales_report': {
                'total_revenue': 0.0,
                'total_orders': 0,
                'average_order_value': 0.0,
                'start_date': start_date,
                'end_date': end_date
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate sales report: {str(e)}'}), 500


@admin_bp.route('/reports/products', methods=['GET'])
@permission_required('view_reports')
def get_product_report():
    """Get product performance report"""
    try:
        product_model = Product()
        category_model = Category()
        
        # Get product performance
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
        
        return jsonify({
            'product_report': {
                'products': product_data[:20],  # Top 20
                'total_products': len(products)
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to generate product report: {str(e)}'}), 500