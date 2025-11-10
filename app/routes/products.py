"""
Products Routes
Handles product browsing, searching, and category management
Updated to use psycopg2-based models
"""

from flask import Blueprint, request, jsonify, render_template

from app.models import Product, Category

# Create blueprint
products_bp = Blueprint('products', __name__)


# ============================================
# CATEGORY ROUTES
# ============================================

@products_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all active categories
    
    Query Parameters:
        - include_inactive: boolean (optional, default=false)
    
    Returns:
        JSON list of categories with product counts
    """
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
                'description': category.get('description'),
                'is_active': category.get('is_active'),
                'display_order': category.get('display_order'),
                'product_count': category_model.get_active_product_count(category['category_id']),
                'created_at': category['created_at'].isoformat() if category.get('created_at') else None
            })
        
        return jsonify({'categories': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get categories: {str(e)}'}), 500


@products_bp.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """
    Get category details with products
    
    Returns:
        JSON category details with product list
    """
    try:
        category_model = Category()
        category = category_model.get_by_id(category_id)
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Get active products in this category
        product_model = Product()
        products_list = product_model.get_by_category(category_id)
        products_list = [p for p in products_list if p.get('is_active')]
        
        products = [
            {
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'is_active': p.get('is_active')
            }
            for p in products_list
        ]
        
        return jsonify({
            'category': {
                'category_id': category['category_id'],
                'category_name': category['category_name'],
                'description': category.get('description'),
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

@products_bp.route('/', methods=['GET'])
@products_bp.route('/list', methods=['GET'])
def get_products():
    """
    Get products with filtering and pagination
    
    Query Parameters:
        - category_id: int (optional) - filter by category
        - search: string (optional) - search in name and description
        - min_price: float (optional) - minimum price filter
        - max_price: float (optional) - maximum price filter
        - page: int (optional, default=1) - page number
        - per_page: int (optional, default=20) - items per page
        - sort_by: string (optional, default='name') - sort field (name, price, newest)
        - sort_order: string (optional, default='asc') - sort order (asc, desc)
    
    Returns:
        JSON list of products with pagination info
    """
    # Get query parameters
    category_id = request.args.get('category_id', type=int)
    search_term = request.args.get('search', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    try:
        product_model = Product()
        category_model = Category()
        
        # Get all active products
        products = product_model.get_all(active_only=True)
        
        # Filter by category
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
        else:  # default to name
            products.sort(key=lambda x: x.get('product_name', '').lower(), reverse=(sort_order == 'desc'))
        
        # Get total count
        total_products = len(products)
        
        # Pagination
        offset = (page - 1) * per_page
        products = products[offset:offset + per_page]
        
        # Format results
        result = []
        for product in products:
            category = category_model.get_by_id(product['category_id'])
            
            result.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'description': product.get('description'),
                'base_price': float(product['base_price']),
                'category': {
                    'category_id': category['category_id'],
                    'category_name': category['category_name']
                } if category else None,
                'is_active': product.get('is_active'),
                'created_at': product['created_at'].isoformat() if product.get('created_at') else None
            })
        
        # Pagination info
        total_pages = (total_products + per_page - 1) // per_page
        
        return jsonify({
            'products': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_products': total_products,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500


@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Get product details by ID
    
    Returns:
        JSON product details
    """
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
                'description': product.get('description'),
                'base_price': float(product['base_price']),
                'category': {
                    'category_id': category['category_id'],
                    'category_name': category['category_name'],
                    'description': category.get('description')
                } if category else None,
                'is_active': product.get('is_active'),
                'created_at': product['created_at'].isoformat() if product.get('created_at') else None,
                'updated_at': product['updated_at'].isoformat() if product.get('updated_at') else None
            }
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get product: {str(e)}'}), 500


# ============================================
# PRODUCT SEARCH
# ============================================

@products_bp.route('/search', methods=['GET'])
def search_products():
    """
    Search products by keyword
    
    Query Parameters:
        - q: string (required) - search query
        - category_id: int (optional) - filter by category
        - limit: int (optional, default=10) - max results
    
    Returns:
        JSON list of matching products
    """
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    limit = min(request.args.get('limit', 10, type=int), 50)  # Max 50 results
    
    if not search_query:
        return jsonify({'error': 'Search query is required'}), 400
    
    if len(search_query) < 2:
        return jsonify({'error': 'Search query must be at least 2 characters'}), 400
    
    try:
        product_model = Product()
        category_model = Category()
        
        search_lower = search_query.lower()
        products = product_model.get_all(active_only=True)
        
        # Search in name and description
        results = [
            p for p in products
            if search_lower in p.get('product_name', '').lower() or
               search_lower in p.get('description', '').lower()
        ]
        
        if category_id:
            results = [p for p in results if p.get('category_id') == category_id]
        
        results = results[:limit]
        
        # Format results
        result = []
        for p in results:
            category = category_model.get_by_id(p['category_id'])
            result.append({
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'category_name': category['category_name'] if category else 'Unknown'
            })
        
        return jsonify({
            'query': search_query,
            'results': result,
            'count': len(result)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


# ============================================
# FEATURED/POPULAR PRODUCTS
# ============================================

@products_bp.route('/featured', methods=['GET'])
def get_featured_products():
    """
    Get featured products (newest products)
    
    Query Parameters:
        - limit: int (optional, default=10)
    
    Returns:
        JSON list of featured products
    """
    limit = min(request.args.get('limit', 10, type=int), 20)
    
    try:
        product_model = Product()
        category_model = Category()
        
        products = product_model.get_all(active_only=True)
        
        # Sort by created_at descending
        products.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        products = products[:limit]
        
        result = []
        for p in products:
            category = category_model.get_by_id(p['category_id'])
            result.append({
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'category_name': category['category_name'] if category else 'Unknown'
            })
        
        return jsonify({'featured_products': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get featured products: {str(e)}'}), 500


@products_bp.route('/popular', methods=['GET'])
def get_popular_products():
    """
    Get popular products (most ordered)
    
    Query Parameters:
        - limit: int (optional, default=10)
    
    Returns:
        JSON list of popular products
    """
    limit = min(request.args.get('limit', 10, type=int), 20)
    
    try:
        product_model = Product()
        category_model = Category()
        
        products = product_model.get_all(active_only=True)
        
        # Get order counts for each product
        product_stats = []
        for product in products:
            order_count = product_model.get_total_orders(product['product_id'])
            product_stats.append((product, order_count))
        
        # Sort by order count descending
        product_stats.sort(key=lambda x: x[1], reverse=True)
        product_stats = product_stats[:limit]
        
        result = []
        for p, order_count in product_stats:
            category = category_model.get_by_id(p['category_id'])
            result.append({
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'description': p.get('description'),
                'base_price': float(p['base_price']),
                'category_name': category['category_name'] if category else 'Unknown',
                'times_ordered': order_count
            })
        
        return jsonify({'popular_products': result}), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get popular products: {str(e)}'}), 500


# ============================================
# PRICE RANGE
# ============================================

@products_bp.route('/price-range', methods=['GET'])
def get_price_range():
    """
    Get min and max price of all active products
    
    Returns:
        JSON with min and max prices
    """
    try:
        product_model = Product()
        products = product_model.get_all(active_only=True)
        
        if not products:
            return jsonify({'min_price': 0, 'max_price': 0}), 200
        
        prices = [float(p.get('base_price', 0)) for p in products]
        
        return jsonify({
            'min_price': min(prices),
            'max_price': max(prices)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get price range: {str(e)}'}), 500