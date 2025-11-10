"""
Helpers Module
Utility helper functions for common operations
"""

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid
import os
import re


class PasswordHelper:
    """Helper functions for password management"""
    
    @staticmethod
    def hash_password(password):
        """
        Hash a password using werkzeug's generate_password_hash
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password
        """
        return generate_password_hash(password)
    
    @staticmethod
    def verify_password(password_hash, password):
        """
        Verify a password against its hash
        
        Args:
            password_hash (str): Hashed password
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(password_hash, password)


class FileHelper:
    """Helper functions for file operations"""
    
    @staticmethod
    def generate_unique_filename(original_filename, prefix=''):
        """
        Generate a unique filename to prevent collisions
        
        Args:
            original_filename (str): Original filename
            prefix (str): Optional prefix for the filename
            
        Returns:
            str: Unique filename
        """
        # Secure the filename
        filename = secure_filename(original_filename)
        
        # Split name and extension
        name, ext = os.path.splitext(filename)
        
        # Generate unique identifier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        
        # Construct new filename
        if prefix:
            new_filename = f"{prefix}_{name}_{timestamp}_{unique_id}{ext}"
        else:
            new_filename = f"{name}_{timestamp}_{unique_id}{ext}"
        
        return new_filename
    
    @staticmethod
    def get_file_extension(filename):
        """
        Get file extension from filename
        
        Args:
            filename (str): Filename
            
        Returns:
            str: File extension (lowercase, without dot)
        """
        if not filename or '.' not in filename:
            return ''
        
        return filename.rsplit('.', 1)[1].lower()
    
    @staticmethod
    def format_file_size(size_bytes):
        """
        Format file size in human-readable format
        
        Args:
            size_bytes (int): File size in bytes
            
        Returns:
            str: Formatted file size (e.g., "1.5 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    @staticmethod
    def sanitize_url(url):
        """
        Sanitize URL string
        
        Args:
            url (str): URL to sanitize
            
        Returns:
            str: Cleaned URL
        """
        if not url:
            return ""
        return url.strip()


class PriceHelper:
    """Helper functions for price calculations and formatting"""
    
    @staticmethod
    def format_currency(amount, currency_symbol='$'):
        """
        Format amount as currency
        
        Args:
            amount: Numeric amount
            currency_symbol (str): Currency symbol (default: '$')
            
        Returns:
            str: Formatted currency string
        """
        try:
            return f"{currency_symbol}{float(amount):.2f}"
        except (ValueError, TypeError):
            return f"{currency_symbol}0.00"
    
    @staticmethod
    def calculate_subtotal(items):
        """
        Calculate subtotal from list of items
        
        Args:
            items (list): List of items with 'price' and 'quantity' attributes
            
        Returns:
            float: Subtotal amount
        """
        try:
            return sum(float(item.price) * int(item.quantity) for item in items)
        except (AttributeError, ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def calculate_tax(subtotal, tax_rate=0.13):
        """
        Calculate tax amount
        
        Args:
            subtotal (float): Subtotal amount
            tax_rate (float): Tax rate as decimal (default: 0.13 for 13%)
            
        Returns:
            float: Tax amount
        """
        try:
            return float(subtotal) * tax_rate
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def calculate_total(subtotal, tax=0.0, shipping=0.0, discount=0.0):
        """
        Calculate total amount
        
        Args:
            subtotal (float): Subtotal amount
            tax (float): Tax amount
            shipping (float): Shipping amount
            discount (float): Discount amount
            
        Returns:
            float: Total amount
        """
        try:
            return float(subtotal) + float(tax) + float(shipping) - float(discount)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def calculate_cart_total(cart_items):
        """
        Calculate total from cart items
        
        Args:
            cart_items (list): List of CartItem objects
            
        Returns:
            float: Total amount
        """
        try:
            total = 0.0
            for item in cart_items:
                # Access product base_price and item quantity
                price = float(item.product.base_price)
                quantity = int(item.quantity)
                total += price * quantity
            return total
        except (AttributeError, ValueError, TypeError):
            return 0.0


class DateHelper:
    """Helper functions for date and time operations"""
    
    @staticmethod
    def now():
        """
        Get current datetime
        
        Returns:
            datetime: Current datetime
        """
        return datetime.now()
    
    @staticmethod
    def now_plus_days(days):
        """
        Get datetime X days from now
        
        Args:
            days (int): Number of days to add
            
        Returns:
            datetime: Future datetime
        """
        return datetime.now() + timedelta(days=days)
    
    @staticmethod
    def format_datetime(dt, format='%B %d, %Y at %I:%M %p'):
        """
        Format datetime object
        
        Args:
            dt (datetime): Datetime object
            format (str): Format string (default: 'Month DD, YYYY at HH:MM AM/PM')
            
        Returns:
            str: Formatted datetime string
        """
        if dt is None:
            return ""
        
        try:
            return dt.strftime(format)
        except (AttributeError, ValueError):
            return str(dt)
    
    @staticmethod
    def format_date(dt, format='%B %d, %Y'):
        """
        Format date
        
        Args:
            dt (datetime): Datetime object
            format (str): Format string (default: 'Month DD, YYYY')
            
        Returns:
            str: Formatted date string
        """
        return DateHelper.format_datetime(dt, format)
    
    @staticmethod
    def get_time_ago(dt):
        """
        Get human-readable time ago string
        
        Args:
            dt (datetime): Datetime object
            
        Returns:
            str: Time ago string (e.g., "2 hours ago", "3 days ago")
        """
        if dt is None:
            return ""
        
        try:
            now = datetime.now()
            diff = now - dt
            
            seconds = diff.total_seconds()
            
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif seconds < 2592000:
                weeks = int(seconds / 604800)
                return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            elif seconds < 31536000:
                months = int(seconds / 2592000)
                return f"{months} month{'s' if months != 1 else ''} ago"
            else:
                years = int(seconds / 31536000)
                return f"{years} year{'s' if years != 1 else ''} ago"
        
        except (AttributeError, TypeError):
            return ""
    
    @staticmethod
    def add_days(dt, days):
        """
        Add days to a datetime
        
        Args:
            dt (datetime): Datetime object
            days (int): Number of days to add
            
        Returns:
            datetime: New datetime object
        """
        try:
            return dt + timedelta(days=days)
        except (AttributeError, TypeError):
            return dt


class StringHelper:
    """Helper functions for string operations"""
    
    @staticmethod
    def truncate(text, length=50, suffix='...'):
        """
        Truncate text to specified length
        
        Args:
            text (str): Text to truncate
            length (int): Maximum length
            suffix (str): Suffix to add if truncated (default: '...')
            
        Returns:
            str: Truncated text
        """
        if not text:
            return ""
        
        if len(text) <= length:
            return text
        
        return text[:length - len(suffix)] + suffix
    
    @staticmethod
    def slugify(text):
        """
        Convert text to URL-friendly slug
        
        Args:
            text (str): Text to slugify
            
        Returns:
            str: Slugified text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace spaces and special chars with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        
        # Remove leading/trailing hyphens
        text = text.strip('-')
        
        return text
    
    @staticmethod
    def capitalize_words(text):
        """
        Capitalize each word in text
        
        Args:
            text (str): Text to capitalize
            
        Returns:
            str: Capitalized text
        """
        if not text:
            return ""
        
        return ' '.join(word.capitalize() for word in text.split())
    
    @staticmethod
    def clean(text):
        """
        Clean excessive whitespace from text
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Trim leading/trailing whitespace
        return text.strip()
    
    @staticmethod
    def clean_whitespace(text):
        """
        Alias for clean() - kept for backward compatibility
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        return StringHelper.clean(text)


class SessionHelper:
    """Helper functions for session management"""
    
    @staticmethod
    def generate_session_id():
        """
        Generate a unique session ID
        
        Returns:
            str: Unique session ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def is_authenticated(session):
        """
        Check if user is authenticated
        
        Args:
            session: Flask session object
            
        Returns:
            bool: True if authenticated, False otherwise
        """
        return 'customer_id' in session or 'admin_id' in session
    
    @staticmethod
    def is_admin(session):
        """
        Check if user is admin
        
        Args:
            session: Flask session object
            
        Returns:
            bool: True if admin, False otherwise
        """
        return 'admin_id' in session
    
    @staticmethod
    def get_user_id(session):
        """
        Get current user ID (customer or admin)
        
        Args:
            session: Flask session object
            
        Returns:
            int or None: User ID if authenticated, None otherwise
        """
        return session.get('customer_id') or session.get('admin_id')
    
    @staticmethod
    def verify_cart_access(cart, customer_id=None, session_id=None):
        """
        Verify user has access to cart
        
        Args:
            cart: ShoppingCart object
            customer_id (int, optional): Customer ID
            session_id (str, optional): Session ID
            
        Returns:
            bool: True if user has access, False otherwise
        """
        if customer_id and cart.customer_id == customer_id:
            return True
        if session_id and cart.session_id == session_id:
            return True
        return False


class OrderHelper:
    """Helper functions for order operations"""
    
    @staticmethod
    def generate_order_number(order_id):
        """
        Generate formatted order number
        
        Args:
            order_id (int): Order ID
            
        Returns:
            str: Formatted order number (e.g., "ORD-20240101-00123")
        """
        timestamp = datetime.now().strftime('%Y%m%d')
        return f"ORD-{timestamp}-{order_id:05d}"
    
    @staticmethod
    def get_order_status_display(status):
        """
        Get display text for order status
        
        Args:
            status (str): Order status code
            
        Returns:
            str: Display text
        """
        status_map = {
            'pending': 'Pending',
            'confirmed': 'Confirmed',
            'processing': 'Processing',
            'printing': 'Printing',
            'shipped': 'Shipped',
            'delivered': 'Delivered',
            'cancelled': 'Cancelled',
            'refunded': 'Refunded'
        }
        
        return status_map.get(status.lower(), status.capitalize())
    
    @staticmethod
    def get_order_status_class(status):
        """
        Get Bootstrap CSS class for order status badge
        
        Args:
            status (str): Order status code
            
        Returns:
            str: Bootstrap class name
        """
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'printing': 'primary',
            'shipped': 'success',
            'delivered': 'success',
            'cancelled': 'danger',
            'refunded': 'secondary'
        }
        
        return status_classes.get(status.lower(), 'secondary')


class PaginationHelper:
    """Helper functions for pagination"""
    
    @staticmethod
    def get_pagination_params(request, default_page=1, default_per_page=20):
        """
        Get pagination parameters from request
        
        Args:
            request: Flask request object
            default_page (int): Default page number
            default_per_page (int): Default items per page
            
        Returns:
            tuple: (page, per_page, offset)
        """
        try:
            page = int(request.args.get('page', default_page))
            page = max(1, page)  # Ensure page is at least 1
        except (ValueError, TypeError):
            page = default_page
        
        try:
            per_page = int(request.args.get('per_page', default_per_page))
            per_page = max(1, min(per_page, 100))  # Between 1 and 100
        except (ValueError, TypeError):
            per_page = default_per_page
        
        offset = (page - 1) * per_page
        
        return page, per_page, offset
    
    @staticmethod
    def calculate_total_pages(total_items, per_page):
        """
        Calculate total number of pages
        
        Args:
            total_items (int): Total number of items
            per_page (int): Items per page
            
        Returns:
            int: Total number of pages
        """
        if total_items == 0 or per_page == 0:
            return 0
        
        return (total_items + per_page - 1) // per_page


# Convenience function exports
hash_password = PasswordHelper.hash_password
verify_password = PasswordHelper.verify_password
format_currency = PriceHelper.format_currency
format_datetime = DateHelper.format_datetime
truncate_text = StringHelper.truncate
generate_unique_filename = FileHelper.generate_unique_filename