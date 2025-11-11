"""
Helpers Module
Utility helper functions for common operations
"""

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid, os,  re


class PasswordHelper: 

    # Hash a password using werkzeug's generate_password_hash
    @staticmethod
    def hash_password(password): 
        return generate_password_hash(password)
    

    # Verify a password against its hash
    @staticmethod
    def verify_password(password_hash, password):
        if not password_hash:
            return False
        return check_password_hash(password_hash, password)


"""Helper functions for file operations"""
class FileHelper: 
    
    #  Generate a unique filename to prevent collisions
    @staticmethod
    def generate_unique_filename(original_filename, prefix=''): 
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
    

    #  Get file extension from filename
    @staticmethod
    def get_file_extension(filename): 
        if not filename or '.' not in filename:
            return ''
        
        return filename.rsplit('.', 1)[1].lower()
    

    # Format file size in human-readable format
    @staticmethod
    def format_file_size(size_bytes): 
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    

    # Sanitize URL string
    @staticmethod
    def sanitize_url(url): 
        if not url:
            return ""
        return url.strip()


# Helper functions for price calculations and formatting
class PriceHelper: 
    

    # Format amount as currency
    @staticmethod
    def format_currency(amount, currency_symbol='$'):
        
        try:
            return f"{currency_symbol}{float(amount):.2f}"
        except (ValueError, TypeError):
            return f"{currency_symbol}0.00"
    

    # Calculate subtotal from list of items
    @staticmethod
    def calculate_subtotal(items):
         
        try:
            return sum(float(item.price) * int(item.quantity) for item in items)
        except (AttributeError, ValueError, TypeError):
            return 0.0
    

    # Calculate tax amount
    @staticmethod
    def calculate_tax(subtotal, tax_rate=0.15): 
        try:
            return float(subtotal) * tax_rate
        except (ValueError, TypeError):
            return 0.0
    

    #  Calculate total amount
    @staticmethod
    def calculate_total(subtotal, tax=0.0, shipping=0.0, discount=0.0): 
        try:
            return float(subtotal) + float(tax) + float(shipping) - float(discount)
        except (ValueError, TypeError):
            return 0.0
    

    # Calculate total from cart items
    @staticmethod
    def calculate_cart_total(cart_items): 
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


"""Helper functions for date and time operations"""
class DateHelper: 
    # Get current datetime
    @staticmethod
    def now(): 
        return datetime.now()
    

    #  Get datetime X days from now
    @staticmethod
    def now_plus_days(days): 
        return datetime.now() + timedelta(days=days)
    

    # Format datetime object
    @staticmethod
    def format_datetime(dt, format='%B %d, %Y at %I:%M %p'): 
        if dt is None:
            return ""
        
        try:
            return dt.strftime(format)
        except (AttributeError, ValueError):
            return str(dt)
    
    #  Format date
    @staticmethod
    def format_date(dt, format='%B %d, %Y'):
        return DateHelper.format_datetime(dt, format)
    

    # Get human-readable time ago string
    @staticmethod
    def get_time_ago(dt): 
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
    

    # Add days to a datetime
    @staticmethod
    def add_days(dt, days): 
        try:
            return dt + timedelta(days=days)
        except (AttributeError, TypeError):
            return dt


#  """Helper functions for string operations"""
class StringHelper: 
    #  Truncate text safely to a maximum length.
    # Returns the original text if it's already shorter.
    @staticmethod
    def truncate_text(text, max_length=100, ellipsis='...'): 
        if not text:
            return ''
        if len(text) <= max_length:
            return text
        return text[:max_length - len(ellipsis)].rstrip() + ellipsis
    
 
    @staticmethod
    def slugify(text):
        """Convert text to a URL-friendly slug."""
        if not text:
            return ""
        # Lowercase, remove non-alphanumeric characters, replace spaces with hyphens
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        text = text.strip('-')
        return text

    # Clean excessive whitespace from text
    @staticmethod
    def clean(text): 
        if not text:
            return ""
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Trim leading/trailing whitespace
        return text.strip()
 


"""Helper functions for session management"""
class SessionHelper: 
    
    #  Generate a unique session ID
    @staticmethod
    def generate_session_id(): 
        return str(uuid.uuid4())
    
    # Check if user is authenticated
    @staticmethod
    def is_authenticated(session): 
        return 'customer_id' in session or 'admin_id' in session
    
    # Check if user is admin
    @staticmethod
    def is_admin(session): 
        return 'admin_id' in session
    
    #  Get current user ID (customer or admin)
    @staticmethod
    def get_user_id(session): 
        return session.get('customer_id') or session.get('admin_id')
    
    # Verify user has access to cart
    @staticmethod
    def verify_cart_access(cart, customer_id=None, session_id=None): 
        if customer_id and cart.customer_id == customer_id:
            return True
        if session_id and cart.session_id == session_id:
            return True
        return False


"""Helper functions for order operations"""
class OrderHelper:
   
    # Generate formatted order number
    @staticmethod
    def generate_order_number(order_id): 
        timestamp = datetime.now().strftime('%Y%m%d')
        return f"ORD-{timestamp}-{order_id:05d}"
    

    #  Get display text for order status
    @staticmethod
    def get_order_status_display(status): 
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
    

    #  Get Bootstrap CSS class for order status badge
    @staticmethod
    def get_order_status_class(status): 
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


"""Helper functions for pagination"""
class PaginationHelper:

    """Paginate any list of data (useful for non-SQL results)."""
    @staticmethod
    def paginate_list(data_list, page=1, per_page=10):
        
        if not data_list:
            return {
                "items": [],
                "page": page,
                "per_page": per_page,
                "total_items": 0,
                "total_pages": 0
            }

        total_items = len(data_list)
        total_pages = (total_items + per_page - 1) // per_page  # Ceiling division
        start = (page - 1) * per_page
        end = start + per_page
        paginated = data_list[start:end]

        return {
            "items": paginated,
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages
        }
    

    #  Get pagination parameters from request
    @staticmethod
    def get_pagination_params(request, default_page=1, default_per_page=20): 
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
    

    # Calculate total number of pages
    @staticmethod
    def calculate_total_pages(total_items, per_page): 
        if total_items == 0 or per_page == 0:
            return 0
        
        return (total_items + per_page - 1) // per_page


# Convenience function exports
hash_password = PasswordHelper.hash_password
verify_password = PasswordHelper.verify_password
format_currency = PriceHelper.format_currency
format_datetime = DateHelper.format_datetime
truncate_text = StringHelper.truncate_text
generate_unique_filename = FileHelper.generate_unique_filename