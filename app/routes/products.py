"""
app/routes/products.py
Products Routes
Handles product browsing, searching, and category management
"""
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for
from app.models import Product, Category
from app.utils import PriceHelper, StringHelper, PaginationHelper

# Create blueprint
products_bp = Blueprint('products', __name__)


# ============================================================
# CATEGORY ROUTES
# ============================================================

@products_bp.route('/categories', methods=['GET'])
def get_categories():
    """Display all product categories."""
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    wants_json = request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']

    try:
        category_model = Category()
        categories = category_model.get_all()

        if not include_inactive:
            categories = [c for c in categories if c.get('is_active')]

        # Sort by order and name
        categories.sort(key=lambda x: (x.get('display_order', 0), x.get('category_name', '')))

        # Format data
        result = [{
            'category_id': c['category_id'],
            'category_name': c['category_name'],
            'description': StringHelper.truncate_text(c.get('description'), 100),
            'is_active': c.get('is_active'),
            'display_order': c.get('display_order'),
            'product_count': category_model.get_active_product_count(c['category_id']),
            'slug': StringHelper.slugify(c['category_name']),
            'created_at': c['created_at'].isoformat() if c.get('created_at') else None
        } for c in categories]

        # JSON only if explicitly requested
        if wants_json:
            return jsonify({'categories': result}), 200

        return render_template('products/categories.html', categories=result)

    except Exception as e:
        if wants_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Failed to get categories: {str(e)}', 'error')
        return redirect(url_for('main.homepage'))


@products_bp.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Show a single category and its active products."""
    wants_json = request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']

    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)
        if not category:
            if wants_json:
                return jsonify({'error': 'Category not found'}), 404
            flash('Category not found', 'error')
            return render_template('errors/404.html'), 404

        product_model = Product()
        products = [p for p in product_model.get_by_category(category_id) if p.get('is_active')]

        product_data = [{
            'product_id': p['product_id'],
            'product_name': p['product_name'],
            'description': StringHelper.truncate_text(p.get('description'), 120),
            'base_price': float(p['base_price']),
            'base_price_formatted': PriceHelper.format_currency(p['base_price']),
            'slug': StringHelper.slugify(p['product_name']),
        } for p in products]

        category_data = {
            'category_id': category['category_id'],
            'category_name': category['category_name'],
            'description': category.get('description'),
            'slug': StringHelper.slugify(category['category_name']),
            'is_active': category.get('is_active'),
            'product_count': len(product_data),
            'products': product_data
        }

        if wants_json:
            return jsonify({'category': category_data}), 200

        return render_template('products/category_detail.html', category=category_data)

    except Exception as e:
        if wants_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Failed to get category: {str(e)}', 'error')
        return redirect(url_for('products.get_categories'))


# ============================================================
# PRODUCT LISTING ROUTES
# ============================================================


@products_bp.route('/list', methods=['GET'])
def get_products():
    """Display all products with filtering, search, and pagination."""
    category_id = request.args.get('category_id', type=int)
    search_term = request.args.get('search', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    wants_json = request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']

    try:
        product_model = Product()
        category_model = Category()

        products = product_model.get_all(active_only=True)

        # --- Filters ---
        if category_id:
            products = [p for p in products if p.get('category_id') == category_id]

        if search_term:
            s = search_term.lower()
            products = [p for p in products if s in p.get('product_name', '').lower() or s in p.get('description', '').lower()]

        if min_price is not None:
            products = [p for p in products if float(p.get('base_price', 0)) >= min_price]
        if max_price is not None:
            products = [p for p in products if float(p.get('base_price', 0)) <= max_price]

        # --- Sorting ---
        if sort_by == 'price':
            products.sort(key=lambda x: float(x.get('base_price', 0)), reverse=(sort_order == 'desc'))
        elif sort_by == 'newest':
            products.sort(key=lambda x: x.get('created_at') or '', reverse=(sort_order == 'desc'))
        else:
            products.sort(key=lambda x: x.get('product_name', '').lower(), reverse=(sort_order == 'desc'))

        # --- Pagination ---
        paginated = PaginationHelper.paginate_list(products, page, per_page)

        result = []
        for p in paginated['items']:
            category = category_model.get_by_id(p['category_id'])
            product_name_lower = p['product_name'].lower()

            # Determine image based on product name
            if 'mug' in product_name_lower:
                image_filename = 'images/mug.png'
            elif 'tote' in product_name_lower:
                image_filename = 'images/tote.png'
            elif 'drawstring' in product_name_lower:
                image_filename = 'images/drawstring-bag.png'
            elif 'shopping' in product_name_lower:
                image_filename = 'images/shopping-bag.png'
            elif 't-shirt' in product_name_lower or 'tshirt' in product_name_lower:
                image_filename = 'images/shirt.png'
            elif 'tumbler' in product_name_lower:
                image_filename = 'images/tumbler.png'
            else:
                image_filename = 'images/mug.png'  # fallback

            
            result.append({
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
                'image_url': url_for('static', filename=image_filename),
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

        # JSON for API / HTML for browsers
        if wants_json:
            return jsonify({'products': result, 'pagination': pagination_data}), 200

        # --- HTML Rendering ---
        all_categories = [c for c in category_model.get_all() if c.get('is_active')]
        categories_for_template = [{'category_id': c['category_id'], 'category_name': c['category_name']} for c in all_categories]

        return render_template('products/list.html',
                               products=result,
                               pagination=pagination_data,
                               categories=categories_for_template,
                               current_category=category_id,
                               search_term=search_term,
                               sort_by=sort_by,
                               sort_order=sort_order)

    except Exception as e:
        if wants_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Failed to get products: {str(e)}', 'error')
        return redirect(url_for('main.homepage'))


# ============================================================
# PRODUCT DESIGN PAGE (NEW)
# ============================================================

@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Show product design customization page."""
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)

        if not product or not product.get('is_active'):
            flash('Product not found or unavailable', 'error')
            return render_template('errors/404.html'), 404

        category_model = Category()
        category = category_model.get_by_id(product['category_id'])

        product_data = {
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'slug': StringHelper.slugify(product['product_name']),
            'description': product.get('description'),
            'base_price': float(product['base_price']),
            'base_price_formatted': PriceHelper.format_currency(product['base_price']),
            'category': {
                'category_id': category['category_id'],
                'category_name': category['category_name'],
                'description': StringHelper.truncate_text(category.get('description'))
            } if category else None,
            'is_active': product.get('is_active'),
            'created_at': product['created_at'].isoformat() if product.get('created_at') else None,
            'updated_at': product['updated_at'].isoformat() if product.get('updated_at') else None
        }

        return render_template('products/design.html', product=product_data)

    except Exception as e:
        flash(f'Failed to get product: {str(e)}', 'error')
        return redirect(url_for('products.get_products'))


@products_bp.route('/<int:product_id>/upload-design', methods=['POST'])
def upload_design(product_id):
    """Handle design upload for a product."""
    if 'design' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['design']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        from app.services.design_service import DesignService
        from flask import current_app
        
        # Get customer/session info
        customer_id = session.get('customer_id')
        session_id = session.get('session_id')
        
        # Ensure guest has session
        if not customer_id and not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            session.permanent = True
        
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Process design upload
        success, result = DesignService.process_design_upload(
            file=file,
            product_id=product_id,
            customer_id=customer_id,
            session_id=session_id,
            upload_folder=upload_folder
        )
        
        if not success:
            return jsonify({'error': result}), 400
        
        return jsonify({
            'message': 'Design uploaded successfully',
            'design': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


# ============================================================
# PRODUCT SEARCH
# ============================================================

@products_bp.route('/search', methods=['GET'])
def search_products():
    """Redirect to products list with search parameter."""
    query = request.args.get('q', '').strip()
    
    if not query:
        flash('Please enter a search term', 'error')
        return redirect(url_for('products.get_products'))
    
    return redirect(url_for('products.get_products', search=query))