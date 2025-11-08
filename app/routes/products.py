"""
Products Routes
Handles product browsing, searching, and category management
"""

from flask import Blueprint, request, jsonify, render_template
from sqlalchemy import or_, func

from app.database import get_db_session
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
        with get_db_session() as db_session:
            query = db_session.query(Category)
            
            if not include_inactive:
                query = query.filter_by(is_active=True)
            
            categories = query.order_by(Category.display_order, Category.category_name).all()
            
            result = []
            for category in categories:
                result.append({
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'is_active': category.is_active,
                    'display_order': category.display_order,
                    'product_count': category.get_active_product_count(),
                    'created_at': category.created_at.isoformat() if category.created_at else None
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
        with get_db_session() as db_session:
            category = db_session.query(Category).filter_by(
                category_id=category_id
            ).first()
            
            if not category:
                return jsonify({'error': 'Category not found'}), 404
            
            # Get active products in this category
            products = [
                {
                    'product_id': p.product_id,
                    'product_name': p.product_name,
                    'description': p.description,
                    'base_price': float(p.base_price),
                    'is_active': p.is_active
                }
                for p in category.get_active_products()
            ]
            
            return jsonify({
                'category': {
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'description': category.description,
                    'is_active': category.is_active,
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
        with get_db_session() as db_session:
            # Base query - only active products
            query = db_session.query(Product).filter_by(is_active=True)
            
            # Filter by category
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            # Search filter
            if search_term:
                search_pattern = f'%{search_term}%'
                query = query.filter(
                    or_(
                        Product.product_name.ilike(search_pattern),
                        Product.description.ilike(search_pattern)
                    )
                )
            
            # Price filters
            if min_price is not None:
                query = query.filter(Product.base_price >= min_price)
            if max_price is not None:
                query = query.filter(Product.base_price <= max_price)
            
            # Sorting
            if sort_by == 'price':
                sort_column = Product.base_price
            elif sort_by == 'newest':
                sort_column = Product.created_at
            else:  # default to name
                sort_column = Product.product_name
            
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Get total count
            total_products = query.count()
            
            # Pagination
            offset = (page - 1) * per_page
            products = query.offset(offset).limit(per_page).all()
            
            # Format results
            result = []
            for product in products:
                result.append({
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'description': product.description,
                    'base_price': float(product.base_price),
                    'category': {
                        'category_id': product.category.category_id,
                        'category_name': product.category.category_name
                    },
                    'is_active': product.is_active,
                    'created_at': product.created_at.isoformat() if product.created_at else None
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
        with get_db_session() as db_session:
            product = db_session.query(Product).filter_by(
                product_id=product_id,
                is_active=True
            ).first()
            
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            return jsonify({
                'product': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'description': product.description,
                    'base_price': float(product.base_price),
                    'category': {
                        'category_id': product.category.category_id,
                        'category_name': product.category.category_name,
                        'description': product.category.description
                    },
                    'is_active': product.is_active,
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'updated_at': product.updated_at.isoformat() if product.updated_at else None
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
        with get_db_session() as db_session:
            search_pattern = f'%{search_query}%'
            
            query = db_session.query(Product).filter(
                Product.is_active == True,
                or_(
                    Product.product_name.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            products = query.limit(limit).all()
            
            result = [
                {
                    'product_id': p.product_id,
                    'product_name': p.product_name,
                    'description': p.description,
                    'base_price': float(p.base_price),
                    'category_name': p.category.category_name
                }
                for p in products
            ]
            
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
        with get_db_session() as db_session:
            products = db_session.query(Product).filter_by(
                is_active=True
            ).order_by(
                Product.created_at.desc()
            ).limit(limit).all()
            
            result = [
                {
                    'product_id': p.product_id,
                    'product_name': p.product_name,
                    'description': p.description,
                    'base_price': float(p.base_price),
                    'category_name': p.category.category_name
                }
                for p in products
            ]
            
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
        with get_db_session() as db_session:
            # Get products with order counts
            from app.models import OrderItem
            
            popular_products = db_session.query(
                Product,
                func.count(OrderItem.order_item_id).label('order_count')
            ).join(
                OrderItem, Product.product_id == OrderItem.product_id
            ).filter(
                Product.is_active == True
            ).group_by(
                Product.product_id
            ).order_by(
                func.count(OrderItem.order_item_id).desc()
            ).limit(limit).all()
            
            result = [
                {
                    'product_id': p.product_id,
                    'product_name': p.product_name,
                    'description': p.description,
                    'base_price': float(p.base_price),
                    'category_name': p.category.category_name,
                    'times_ordered': order_count
                }
                for p, order_count in popular_products
            ]
            
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
        with get_db_session() as db_session:
            result = db_session.query(
                func.min(Product.base_price).label('min_price'),
                func.max(Product.base_price).label('max_price')
            ).filter_by(is_active=True).first()
            
            return jsonify({
                'min_price': float(result.min_price) if result.min_price else 0,
                'max_price': float(result.max_price) if result.max_price else 0
            }), 200
            
    except Exception as e:
        return jsonify({'error': f'Failed to get price range: {str(e)}'}), 500