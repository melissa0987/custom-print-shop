"""
Product Service
Business logic for product and category management
"""

from sqlalchemy import or_, func
from app.database import get_db_session
from app.models.__models_init__ import Product, Category, OrderItem
from app.utils.__utils_init__ import (
    Validators,
    StringHelper,
    PriceHelper,
    PaginationHelper,
    DateHelper
)


class ProductService:
    """Service class for product operations"""
    
    @staticmethod
    def get_all_products(category_id=None, search_term=None, min_price=None,
                         max_price=None, is_active=True, page=1, per_page=20,
                         sort_by='name', sort_order='asc'):
        """
        Get products with filtering and pagination
        
        Args:
            category_id (int, optional): Filter by category
            search_term (str, optional): Search in name and description
            min_price (float, optional): Minimum price
            max_price (float, optional): Maximum price
            is_active (bool): Filter active products only
            page (int): Page number
            per_page (int): Items per page
            sort_by (str): Sort field (name, price, newest)
            sort_order (str): Sort order (asc, desc)
            
        Returns:
            tuple: (products, total_count, total_pages)
        """
        try:
            with get_db_session() as session:
                query = session.query(Product)

                if is_active:
                    query = query.filter_by(is_active=True)

                if category_id:
                    query = query.filter_by(category_id=category_id)

                if search_term:
                    search_term = StringHelper.clean_whitespace(search_term)
                    pattern = f"%{search_term}%"
                    query = query.filter(
                        or_(
                            Product.product_name.ilike(pattern),
                            Product.description.ilike(pattern)
                        )
                    )

                # Price filters (validate numeric)
                if min_price is not None:
                    valid, msg = Validators.validate_price(min_price)
                    if valid:
                        query = query.filter(Product.base_price >= float(min_price))
                if max_price is not None:
                    valid, msg = Validators.validate_price(max_price)
                    if valid:
                        query = query.filter(Product.base_price <= float(max_price))

                # Sorting
                if sort_by == 'price':
                    sort_col = Product.base_price
                elif sort_by == 'newest':
                    sort_col = Product.created_at
                else:
                    sort_col = Product.product_name

                if sort_order == 'desc':
                    query = query.order_by(sort_col.desc())
                else:
                    query = query.order_by(sort_col.asc())

                total_count = query.count()
                total_pages = PaginationHelper.calculate_total_pages(total_count, per_page)
                offset = (max(page, 1) - 1) * per_page

                products = query.offset(offset).limit(per_page).all()
                return products, total_count, total_pages

        except Exception as e:
            print(f"[ProductService] Error getting products: {e}")
            return [], 0, 0
    
    @staticmethod
    def get_product_by_id(product_id, is_active=True):
        """
        Get product by ID
        
        Args:
            product_id (int): Product ID
            is_active (bool): Check if product is active
            
        Returns:
            Product or None
        """
        try:
            with get_db_session() as session:
                query = session.query(Product).filter_by(product_id=product_id)
                if is_active:
                    query = query.filter_by(is_active=True)
                return query.first()
        except Exception:
            return None
    
    @staticmethod
    def search_products(search_query, category_id=None, limit=10):
        """
        Search products by keyword
        
        Args:
            search_query (str): Search query
            category_id (int, optional): Filter by category
            limit (int): Maximum results
            
        Returns:
            list: List of products
        """
        if not search_query:
            return []
        try:
            with get_db_session() as session:
                search_query = StringHelper.clean_whitespace(search_query)
                pattern = f"%{search_query}%"

                query = session.query(Product).filter(
                    Product.is_active.is_(True),
                    or_(
                        Product.product_name.ilike(pattern),
                        Product.description.ilike(pattern)
                    )
                )

                if category_id:
                    query = query.filter_by(category_id=category_id)

                return query.limit(limit).all()
        except Exception:
            return []
    
    @staticmethod
    def get_featured_products(limit=10):
        """
        Get featured products (newest)
        
        Args:
            limit (int): Number of products
            
        Returns:
            list: List of products
        """
        try:
            with get_db_session() as session:
                return (
                    session.query(Product)
                    .filter_by(is_active=True)
                    .order_by(Product.created_at.desc())
                    .limit(limit)
                    .all()
                )
        except Exception:
            return []
        
    
    @staticmethod
    def get_popular_products(limit=10):
        """
        Get popular products (most ordered)
        
        Args:
            limit (int): Number of products
            
        Returns:
            list: List of tuples (product, order_count)
        """
        try:
            with get_db_session() as session:
                return (
                    session.query(
                        Product,
                        func.count(OrderItem.order_item_id).label("order_count")
                    )
                    .join(OrderItem, Product.product_id == OrderItem.product_id)
                    .filter(Product.is_active.is_(True))
                    .group_by(Product.product_id)
                    .order_by(func.count(OrderItem.order_item_id).desc())
                    .limit(limit)
                    .all()
                )
        except Exception:
            return []
    
    @staticmethod
    def get_price_range():
        """
        Get min and max price of active products
        
        Returns:
            tuple: (min_price, max_price)
        """
        try:
            with get_db_session() as session:
                result = (
                    session.query(
                        func.min(Product.base_price).label("min_price"),
                        func.max(Product.base_price).label("max_price"),
                    )
                    .filter_by(is_active=True)
                    .first()
                )
                return (
                    float(result.min_price) if result.min_price else 0.0,
                    float(result.max_price) if result.max_price else 0.0,
                )
        except Exception:
            return 0.0, 0.0
    
    @staticmethod
    def get_all_categories(include_inactive=False):
        """
        Get all categories
        
        Args:
            include_inactive (bool): Include inactive categories
            
        Returns:
            list: List of categories
        """
        try:
            with get_db_session() as session:
                query = session.query(Category)
                if not include_inactive:
                    query = query.filter_by(is_active=True)
                return query.order_by(Category.display_order, Category.category_name).all()
        except Exception:
            return []
    
    @staticmethod
    def get_category_by_id(category_id, include_inactive=False):
        """
        Get category by ID
        
        Args:
            category_id (int): Category ID
            include_inactive (bool): Include inactive category
            
        Returns:
            Category or None
        """
        try:
            with get_db_session() as session:
                query = session.query(Category).filter_by(category_id=category_id)
                if not include_inactive:
                    query = query.filter_by(is_active=True)
                return query.first()
        except Exception:
            return None

    
    @staticmethod
    def get_products_by_category(category_id, is_active=True):
        """
        Get products in a category
        
        Args:
            category_id (int): Category ID
            is_active (bool): Filter active products
            
        Returns:
            list: List of products
        """
        try:
            with get_db_session() as session:
                query = session.query(Product).filter_by(category_id=category_id)
                if is_active:
                    query = query.filter_by(is_active=True)
                return query.order_by(Product.product_name.asc()).all()
        except Exception:
            return []
    
    @staticmethod
    def get_product_statistics(product_id):
        """
        Get product statistics
        
        Args:
            product_id (int): Product ID
            
        Returns:
            dict: Product statistics
        """
        try:
            with get_db_session() as session:
                product = session.query(Product).filter_by(product_id=product_id).first()
                if not product:
                    return None

                return {
                    "times_ordered": getattr(product, "get_times_ordered", lambda: 0)(),
                    "total_quantity_sold": getattr(product, "get_total_quantity_sold", lambda: 0)(),
                    "total_revenue": float(
                        getattr(product, "get_total_revenue", lambda: 0.0)() or 0.0
                    ),
                }
        except Exception:
            return None
    
    @staticmethod
    def update_product(admin_id, product_id, **kwargs):
        """
        Update product (admin only)
        
        Args:
            admin_id (int): Admin ID
            product_id (int): Product ID
            **kwargs: Fields to update
            
        Returns:
            tuple: (success: bool, product or error_message)
        """
        allowed_fields = ["product_name", "description", "base_price", "is_active", "category_id"]

        try:
            with get_db_session() as session:
                product = session.query(Product).filter_by(product_id=product_id).first()
                if not product:
                    return False, "Product not found"

                # Validate and sanitize inputs
                for key, value in kwargs.items():
                    if key not in allowed_fields:
                        continue

                    if key == "base_price":
                        valid, msg = Validators.validate_price(value)
                        if not valid:
                            return False, msg
                        value = float(value)

                    elif key in ("product_name", "description"):
                        value = StringHelper.clean_whitespace(value)

                    setattr(product, key, value)

                product.updated_by = admin_id
                return True, product

        except Exception as e:
            return False, f"Failed to update product: {str(e)}"
    
    @staticmethod
    def create_product(admin_id, category_id, product_name, description, base_price):
        """
        Create new product (admin only)
        
        Args:
            admin_id (int): Admin ID
            category_id (int): Category ID
            product_name (str): Product name
            description (str): Description
            base_price (float): Base price
            
        Returns:
            tuple: (success: bool, product or error_message)
        """
        # Input sanitization
        product_name = StringHelper.clean_whitespace(product_name)
        description = StringHelper.clean_whitespace(description)

        # Validation
        if not product_name:
            return False, "Product name is required"
        valid_price, msg = Validators.validate_price(base_price)
        if not valid_price:
            return False, msg

        try:
            with get_db_session() as session:
                category = session.query(Category).filter_by(category_id=category_id).first()
                if not category:
                    return False, "Category not found"

                product = Product(
                    category_id=category_id,
                    product_name=product_name,
                    description=description,
                    base_price=float(base_price),
                    created_by=admin_id,
                    updated_by=admin_id,
                    is_active=True
                )
                session.add(product)
                session.flush()

                return True, product

        except Exception as e:
            return False, f"Failed to create product: {str(e)}"
