"""
Validators Module
Input validation functions for the custom printing website
"""

import re
from datetime import datetime


class Validators:
    """Collection of validation functions"""
    
    @staticmethod
    def validate_email(email):
        """
        Validate email format
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    @staticmethod
    def validate_username(username):
        """
        Validate username format (3-50 chars, alphanumeric, underscore, hyphen)
        
        Args:
            username (str): Username to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not username or not isinstance(username, str):
            return False
        
        pattern = r'^[a-z0-9_-]{3,50}$'
        return re.match(pattern, username.strip(), re.IGNORECASE) is not None
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength
        Requirements: min 8 chars, at least 1 letter and 1 number
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not password or not isinstance(password, str):
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[a-zA-Z]', password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_phone_number(phone):
        """
        Validate phone number format (flexible international format)
        
        Args:
            phone (str): Phone number to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not phone:
            return True  # Phone is optional
        
        if not isinstance(phone, str):
            return False
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it's all digits (possibly with + prefix)
        pattern = r'^\+?\d{10,15}$'
        return re.match(pattern, cleaned) is not None
    
    @staticmethod
    def validate_price(price):
        """
        Validate price (must be positive number)
        
        Args:
            price: Price value to validate
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            price_float = float(price)
            if price_float < 0:
                return False, "Price must be non-negative"
            if price_float > 999999.99:
                return False, "Price is too large"
            return True, "Price is valid"
        except (ValueError, TypeError):
            return False, "Price must be a valid number"
    
    @staticmethod
    def validate_quantity(quantity):
        """
        Validate quantity (must be positive integer)
        
        Args:
            quantity: Quantity value to validate
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            quantity_int = int(quantity)
            if quantity_int < 1:
                return False, "Quantity must be at least 1"
            if quantity_int > 10000:
                return False, "Quantity exceeds maximum allowed (10,000)"
            return True, "Quantity is valid"
        except (ValueError, TypeError):
            return False, "Quantity must be a valid integer"
    
    @staticmethod
    def validate_file_extension(filename, allowed_extensions=None):
        """
        Validate file extension
        
        Args:
            filename (str): Filename to validate
            allowed_extensions (set): Set of allowed extensions (default: common image/design formats)
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not filename or not isinstance(filename, str):
            return False
        
        if allowed_extensions is None:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}
        
        if '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in allowed_extensions
    
    @staticmethod
    def validate_file_size(file_size, max_size_mb=16):
        """
        Validate file size
        
        Args:
            file_size (int): File size in bytes
            max_size_mb (int): Maximum size in megabytes (default: 16MB)
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                return False, f"File size exceeds maximum allowed ({max_size_mb}MB)"
            return True, "File size is valid"
        except (ValueError, TypeError):
            return False, "Invalid file size"
    
    @staticmethod
    def validate_order_status(status):
        """
        Validate order status
        
        Args:
            status (str): Order status to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        valid_statuses = {
            'pending', 'confirmed', 'processing', 
            'printing', 'shipped', 'delivered', 
            'cancelled', 'refunded'
        }
        return status and status.lower() in valid_statuses
    
    @staticmethod
    def validate_role(role):
        """
        Validate admin role
        
        Args:
            role (str): Role to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        valid_roles = {'super_admin', 'admin', 'staff'}
        return role and role.lower() in valid_roles
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """
        Validate that all required fields are present and non-empty
        
        Args:
            data (dict): Data dictionary to validate
            required_fields (list): List of required field names
            
        Returns:
            tuple: (is_valid: bool, missing_fields: list)
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def sanitize_string(text, max_length=None):
        """
        Sanitize string input (trim whitespace, limit length)
        
        Args:
            text (str): Text to sanitize
            max_length (int, optional): Maximum length
            
        Returns:
            str: Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Trim whitespace
        sanitized = text.strip()
        
        # Limit length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_text_length(text, min_length=0, max_length=None):
        """
        Validate text length
        
        Args:
            text (str): Text to validate
            min_length (int): Minimum length (default: 0)
            max_length (int, optional): Maximum length
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not isinstance(text, str):
            return False, "Text must be a string"
        
        text_length = len(text.strip())
        
        if text_length < min_length:
            return False, f"Text must be at least {min_length} characters"
        
        if max_length and text_length > max_length:
            return False, f"Text must not exceed {max_length} characters"
        
        return True, "Text length is valid"
    
    @staticmethod
    def validate_customization_text(text):
        """
        Validate customization text (for printing on products)
        
        Args:
            text (str): Customization text
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
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


# Convenience functions for backward compatibility
def validate_email(email):
    """Validate email format"""
    return Validators.validate_email(email)


def validate_username(username):
    """Validate username format"""
    return Validators.validate_username(username)


def validate_password(password):
    """Validate password strength"""
    return Validators.validate_password_strength(password)


def validate_phone_number(phone):
    """Validate phone number format"""
    return Validators.validate_phone_number(phone)