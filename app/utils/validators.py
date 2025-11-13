"""
app/utils/validators.py
Validators Module
Input validation functions for the custom printing website 
"""

import re, logging 

logger = logging.getLogger(__name__)


"""Collection of validation functions"""
class Validators: 
    
    #  Validate email format
    @staticmethod
    def validate_email(email):
         
        if not email or not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    

    #  Validate username format (3-50 chars, alphanumeric, underscore, hyphen)
    @staticmethod
    def validate_username(username): 
        if not username or not isinstance(username, str):
            return False
        
        pattern = r'^[a-z0-9_-]{3,50}$'
        return re.match(pattern, username.strip(), re.IGNORECASE) is not None
    

    # Validate password strength
    # Requirements: min 8 chars, at least 1 letter and 1 number
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength
        Requirements: 
        - Min 8 chars
        - At least 1 letter
        - At least 1 number
        - At least 1 special character
        """
        if not password or not isinstance(password, str):
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[a-zA-Z]', password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            return False, "Password must contain at least one special character (!@#$%^&* etc.)"
        
        return True, "Password is valid"
    
    
    
    # Validate phone number format (flexible international format)
    @staticmethod
    def validate_phone_number(phone): 
        if not phone:
            return True  # Phone is optional
        
        if not isinstance(phone, str):
            return False
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it's all digits (possibly with + prefix)
        pattern = r'^\+?\d{10,15}$'
        return re.match(pattern, cleaned) is not None
    

    # Validate price (must be non-negative number)
    @staticmethod
    def validate_price(price): 
        try:
            price_float = float(price)
            if price_float < 0:
                return False, "Price must be non-negative"
            if price_float > 999999.99:
                return False, "Price is too large (max: 999,999.99)"
            return True, "Price is valid"
        except (ValueError, TypeError):
            return False, "Price must be a valid number"
    
    # Validate quantity (must be positive integer)
    @staticmethod
    def validate_quantity(quantity): 
        try:
            quantity_int = int(quantity)
            if quantity_int < 1:
                return False, "Quantity must be at least 1"
            if quantity_int > 10000:
                return False, "Quantity exceeds maximum allowed (10,000)"
            return True, "Quantity is valid"
        except (ValueError, TypeError):
            return False, "Quantity must be a valid integer"
    

    # Validate file extension
    @staticmethod
    def validate_file_extension(filename, allowed_extensions=None): 
        if not filename or not isinstance(filename, str):
            return False
        
        if allowed_extensions is None:
            # Default allowed extensions for custom printing
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd', 'eps'}
        
        if '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in allowed_extensions
    
    # Validate file size
    @staticmethod
    def validate_file_size(file_size, max_size_mb=16): 
        try:
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                return False, f"File size exceeds maximum allowed ({max_size_mb}MB)"
            return True, "File size is valid"
        except (ValueError, TypeError):
            return False, "Invalid file size"
    

    # Validate order status
    @staticmethod
    def validate_order_status(status): 
        valid_statuses = {'pending', 'processing', 'completed', 'cancelled'}
        return status and status.lower() in valid_statuses
    

    # Validate admin role
    @staticmethod
    def validate_role(role): 
        valid_roles = {'super_admin', 'admin', 'staff'}
        return role and role.lower() in valid_roles
    

    # Validate that all required fields are present and non-empty
    @staticmethod
    def validate_required_fields(data, required_fields): 
        missing_fields = []
        
        for field in required_fields:
            value = data.get(field)
            # Check if field is missing or empty (handles None, empty string, empty list, etc.)
            if value is None or (isinstance(value, str) and not value.strip()) or \
               (isinstance(value, (list, dict)) and not value):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    

    # Sanitize string input (trim whitespace, limit length)
    @staticmethod
    def sanitize_string(text, max_length=None):
         
        if not text or not isinstance(text, str):
            return ""
        
        # Trim whitespace
        sanitized = text.strip()
        
        # Limit length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    

    # Validate text length
    @staticmethod
    def validate_text_length(text, min_length=0, max_length=None): 
        if not isinstance(text, str):
            return False, "Text must be a string"
        
        text_length = len(text.strip())
        
        if text_length < min_length:
            return False, f"Text must be at least {min_length} characters"
        
        if max_length and text_length > max_length:
            return False, f"Text must not exceed {max_length} characters"
        
        return True, "Text length is valid"
    

    # Validate customization text (for printing on products)
    @staticmethod
    def validate_customization_text(text): 
        if not text:
            return True, "Text is optional"  # Customization text is optional
        
        # Check length (reasonable limit for printing)
        is_valid, message = Validators.validate_text_length(text, min_length=1, max_length=500)
        if not is_valid:
            return is_valid, message
        
        # Check for potentially problematic characters
        # Allow alphanumeric, common punctuation, and spaces
        if not re.match(r'^[a-zA-Z0-9\s\.,!?\'\"-]+$', text):
            return False, "Text contains invalid characters"
        
        return True, "Customization text is valid"
    

    # Validate category name (max 50 chars per schema)
    @staticmethod
    def validate_category_name(name): 
        if not name or not isinstance(name, str):
            return False, "Category name is required"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Category name must be at least 2 characters"
        
        if len(name) > 50:
            return False, "Category name must not exceed 50 characters"
        
        # Allow letters, numbers, spaces, and common punctuation
        if not re.match(r'^[a-zA-Z0-9\s\-&]+$', name):
            return False, "Category name contains invalid characters"
        
        return True, "Category name is valid"
    

    # Validate product name (max 100 chars per schema)
    @staticmethod
    def validate_product_name(name): 
        if not name or not isinstance(name, str):
            return False, "Product name is required"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Product name must be at least 2 characters"
        
        if len(name) > 100:
            return False, "Product name must not exceed 100 characters"
        
        return True, "Product name is valid"
    

    # Validate shipping address
    @staticmethod
    def validate_shipping_address(address): 
        if not address or not isinstance(address, str):
            return False, "Shipping address is required"
        
        address = address.strip()
        
        if len(address) < 10:
            return False, "Shipping address is too short (minimum 10 characters)"
        
        if len(address) > 500:
            return False, "Shipping address is too long (maximum 500 characters)"
        
        return True, "Shipping address is valid"
    

    # Validate order number format (max 50 chars per schema)
    @staticmethod
    def validate_order_number(order_number): 
        if not order_number or not isinstance(order_number, str):
            return False, "Order number is required"
        
        if len(order_number) > 50:
            return False, "Order number is too long (maximum 50 characters)"
        
        # Check if it matches expected format (e.g., ORD-00001)
        if not re.match(r'^[A-Z0-9\-]+$', order_number):
            return False, "Order number contains invalid characters"
        
        return True, "Order number is valid"
    

    # Validate customization key (max 100 chars per schema)
    @staticmethod
    def validate_customization_key(key): 
        if not key or not isinstance(key, str):
            return False, "Customization key is required"
        
        key = key.strip()
        
        if len(key) < 1:
            return False, "Customization key cannot be empty"
        
        if len(key) > 100:
            return False, "Customization key is too long (maximum 100 characters)"
        
        # Allow lowercase letters, numbers, and underscores (like variable names)
        if not re.match(r'^[a-z0-9_]+$', key):
            return False, "Customization key can only contain lowercase letters, numbers, and underscores"
        
        return True, "Customization key is valid"
    

    # Validate display order (for categories)
    @staticmethod
    def validate_display_order(order): 
        try:
            order_int = int(order)
            if order_int < 0:
                return False, "Display order must be non-negative"
            if order_int > 9999:
                return False, "Display order is too large"
            return True, "Display order is valid"
        except (ValueError, TypeError):
            return False, "Display order must be a valid integer"
 

  