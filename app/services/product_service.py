"""
Product Service
Business logic for product and category management
Updated to use psycopg2-based models
"""

from app.models import Product, Category
from app.utils import (
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
            product_model = Product()
            
            # Get all products
            products = product_model.get_all(active_only=is_active)
            
            # Filter by category
            if category_id:
                products = [p for p in products if p.get('category_id') == category_id]
            
            # Search filter
            if search_term:
                search_term = StringHelper.clean_whitespace(search_term).lower()
                products = [
                    p for p in products
                    if search_term in p.get('product_name', '').lower() or
                       search_term in p.get('description', '').lower()
                ]
            
            # Price filters
            if min_price is not None:
                valid, msg = Validators.validate_price(min_price)
                if valid:
                    products = [p for p in products if float(p.get('base_price', 0)) >= float(min_price)]
            
            if max_price is not None:
                valid, msg = Validators.validate_price(max_price)
                if valid:
                    products = [p for p in products if float(p.get('base_price', 0)) <= float(max_price)]
            
            # Sorting
            if sort_by == 'price':
                products.sort(key=lambda x: float(x.get('base_price', 0)), reverse=(sort_order == 'desc'))
            elif sort_by == 'newest':
                products.sort(key=lambda x: x.get('created_at') or '', reverse=(sort_order == 'desc'))
            else:  # name
                products.sort(key=lambda x: x.get('product_name', '').lower(), reverse=(sort_order == 'desc'))
            
            # Pagination
            total_count = len(products)
            total_pages = PaginationHelper.calculate_total_pages(total_count, per_page)
            offset = (max(page, 1) - 1) * per_page
            products = products[offset:offset + per_page]
            
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
            dict or None: Product data
        """
        try:
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product:
                return None
            
            if is_active and not product.get('is_active'):
                return None
            
            return product
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
            product_model = Product()
            search_query = StringHelper.clean_whitespace(search_query).lower()
            
            products = product_model.get_all(active_only=True)
            
            # Search in name and description
            results = [
                p for p in products
                if search_query in p.get('product_name', '').lower() or
                   search_query in p.get('description', '').lower()
            ]
            
            # Filter by category if specified
            if category_id:
                results = [p for p in results if p.get('category_id') == category_id]
            
            return results[:limit]
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
            product_model = Product()
            products = product_model.get_all(active_only=True)
            
            # Sort by created_at descending
            products.sort(key=lambda x: x.get('created_at') or '', reverse=True)
            
            return products[:limit]
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
            product_model = Product()
            products = product_model.get_all(active_only=True)
            
            # Get order counts for each product
            product_stats = []
            for product in products:
                order_count = product_model.get_total_orders(product['product_id'])
                product_stats.append((product, order_count))
            
            # Sort by order count descending
            product_stats.sort(key=lambda x: x[1], reverse=True)
            
            return product_stats[:limit]
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
            product_model = Product()
            products = product_model.get_all(active_only=True)
            
            if not products:
                return 0.0, 0.0
            
            prices = [float(p.get('base_price', 0)) for p in products]
            return min(prices), max(prices)
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
            category_model = Category()
            categories = category_model.get_all()
            
            if not include_inactive:
                categories = [c for c in categories if c.get('is_active')]
            
            # Sort by display_order and category_name
            categories.sort(key=lambda x: (x.get('display_order', 0), x.get('category_name', '')))
            
            return categories
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
            dict or None: Category data
        """
        try:
            category_model = Category()
            category = category_model.get_by_id(category_id)
            
            if not category:
                return None
            
            if not include_inactive and not category.get('is_active'):
                return None
            
            return category
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
            product_model = Product()
            products = product_model.get_by_category(category_id)
            
            if is_active:
                products = [p for p in products if p.get('is_active')]
            
            # Sort by product name
            products.sort(key=lambda x: x.get('product_name', '').lower())
            
            return products
        except Exception:
            return []
    
    @staticmethod
    def get_product_statistics(product_id):
        """
        Get product statistics
        
        Args:
            product_id (int): Product ID
            
        Returns:
            dict: Product statistics or None
        """
        try:
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product:
                return None

            return {
                "times_ordered": product_model.get_total_orders(product_id),
                "total_quantity_sold": product_model.get_total_quantity_sold(product_id),
                "total_revenue": product_model.get_total_revenue(product_id)
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
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product:
                return False, "Product not found"

            # Filter and validate inputs
            update_data = {}
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

                update_data[key] = value

            # Add updated_by
            update_data['updated_by'] = admin_id

            # Update product
            success = product_model.update(product_id, **update_data)
            
            if not success:
                return False, "Failed to update product"

            # Get updated product
            product = product_model.get_by_id(product_id)
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
            category_model = Category()
            category = category_model.get_by_id(category_id)
            
            if not category:
                return False, "Category not found"

            product_model = Product()
            product_id = product_model.create(
                category_id=category_id,
                product_name=product_name,
                description=description,
                base_price=float(base_price),
                is_active=True,
                created_by=admin_id,
                updated_by=admin_id
            )

            # Get created product
            product = product_model.get_by_id(product_id)
            return True, product

        except Exception as e:
            return False, f"Failed to create product: {str(e)}"