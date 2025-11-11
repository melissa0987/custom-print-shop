"""
app/routes/products.py
Products Routes
Handles product browsing, searching, and category management
"""
# TODO: use render_template for html
from flask import Blueprint, request, jsonify

from app.models import Product, Category
from app.utils import PriceHelper, StringHelper, PaginationHelper

# Create blueprint
products_bp = Blueprint('products', __name__)


# ============================================
# CATEGORY ROUTES
# ============================================

# Get all active categories
@products_bp.route('/categories', methods=['GET'])
def get_categories(): 
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    try:
        category_model = Category()
        categories = category_model.get_all()

        if not include_inactive:
            categories = [c for c in categories if c.get('is_active')]

        # Sort by display_order and category_name
        categories.sort(key=lambda x: (x.get('display_order', 0), x.get('category_name', '')))

        result = []
        for category in categories:
            result.append({
                'category_id': category['category_id'],
                'category_name': category['category_name'],
                'description': StringHelper.truncate_text(category.get('description'), 100),
                'is_active': category.get('is_active'),
                'display_order': category.get('display_order'),
                'product_count': category_model.get_active_product_count(category['category_id']),
                'slug': StringHelper.slugify(category['category_name']),
                'created_at': category['created_at'].isoformat() if category.get('created_at') else None
            })

        return jsonify({'categories': result}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get categories: {str(e)}'}), 500


# Get category details with products
@products_bp.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id): 
    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)

        if not category:
            return jsonify({'error': 'Category not found'}), 404

        product_model = Product()
        products_list = product_model.get_by_category(category_id)
        products_list = [p for p in products_list if p.get('is_active')]

        products = [
            {
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'description': StringHelper.truncate_text(p.get('description'), 120),
                'base_price': float(p['base_price']),
                'base_price_formatted': PriceHelper.format_currency(p['base_price']),
                'slug': StringHelper.slugify(p['product_name']),
                'is_active': p.get('is_active')
            }
            for p in products_list
        ]

        return jsonify({
            'category': {
                'category_id': category['category_id'],
                'category_name': category['category_name'],
                'description': StringHelper.truncate_text(category.get('description')),
                'slug': StringHelper.slugify(category['category_name']),
                'is_active': category.get('is_active'),
                'product_count': len(products),
                'products': products
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get category: {str(e)}'}), 500


# ============================================
# PRODUCT LISTING ROUTES
# ============================================

# Get products with filtering and pagination
@products_bp.route('/', methods=['GET'])
@products_bp.route('/list', methods=['GET'])
def get_products(): 

    # Query params
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

        # Get all active products
        products = product_model.get_all(active_only=True)

        # Category filter
        if category_id:
            products = [p for p in products if p.get('category_id') == category_id]

        # Search filter
        if search_term:
            search_lower = search_term.lower()
            products = [
                p for p in products
                if search_lower in p.get('product_name', '').lower() or
                   search_lower in p.get('description', '').lower()
            ]

        # Price filters
        if min_price is not None:
            products = [p for p in products if float(p.get('base_price', 0)) >= min_price]
        if max_price is not None:
            products = [p for p in products if float(p.get('base_price', 0)) <= max_price]

        # Sorting
        if sort_by == 'price':
            products.sort(key=lambda x: float(x.get('base_price', 0)), reverse=(sort_order == 'desc'))
        elif sort_by == 'newest':
            products.sort(key=lambda x: x.get('created_at') or '', reverse=(sort_order == 'desc'))
        else:
            products.sort(key=lambda x: x.get('product_name', '').lower(), reverse=(sort_order == 'desc'))

        # Pagination using PaginationHelper
        paginated = PaginationHelper.paginate_list(products, page, per_page)

        # Format response
        result = []
        for product in paginated['items']:
            category = category_model.get_by_id(product['category_id'])
            result.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'slug': StringHelper.slugify(product['product_name']),
                'description': StringHelper.truncate_text(product.get('description'), 120),
                'base_price': float(product['base_price']),
                'base_price_formatted': PriceHelper.format_currency(product['base_price']),
                'category': {
                    'category_id': category['category_id'],
                    'category_name': category['category_name']
                } if category else None,
                'is_active': product.get('is_active'),
                'created_at': product['created_at'].isoformat() if product.get('created_at') else None
            })

        return jsonify({
            'products': result,
            'pagination': {
                'page': paginated['page'],
                'per_page': paginated['per_page'],
                'total_items': paginated['total_items'],
                'total_pages': paginated['total_pages']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500


# ============================================
# PRODUCT DETAIL
# ============================================

# Get product details by ID
@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id): 
    try:
        product_model = Product()
        product = product_model.get_by_id(product_id)

        if not product or not product.get('is_active'):
            return jsonify({'error': 'Product not found'}), 404

        category_model = Category()
        category = category_model.get_by_id(product['category_id'])

        return jsonify({
            'product': {
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'slug': StringHelper.slugify(product['product_name']),
                'description': StringHelper.truncate_text(product.get('description')),
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
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get product: {str(e)}'}), 500