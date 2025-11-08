"""
Authentication Service
Business logic for user authentication and registration
"""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

from app.database import get_db_session
from app.models import Customer, AdminUser


class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    def validate_email(email):
        """
        Validate email format
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username):
        """
        Validate username format
        
        Args:
            username (str): Username to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pattern = r'^[a-z0-9_-]{3,50}$'
        return re.match(pattern, username, re.IGNORECASE) is not None
    
    @staticmethod
    def validate_password_strength(password):
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple: (is_valid, message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[a-zA-Z]', password):
            return False, "Password must contain at least one letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Valid"
    
    @staticmethod
    def register_customer(username, email, password, first_name, last_name, phone_number=None):
        """
        Register a new customer
        
        Args:
            username (str): Username
            email (str): Email address
            password (str): Password
            first_name (str): First name
            last_name (str): Last name
            phone_number (str, optional): Phone number
            
        Returns:
            tuple: (success: bool, customer or error_message)
        """
        # Validate inputs
        if not AuthService.validate_username(username):
            return False, "Invalid username format"
        
        if not AuthService.validate_email(email):
            return False, "Invalid email format"
        
        is_valid, message = AuthService.validate_password_strength(password)
        if not is_valid:
            return False, message
        
        try:
            with get_db_session() as session:
                # Check for existing username
                existing = session.query(Customer).filter_by(
                    username=username.lower()
                ).first()
                if existing:
                    return False, "Username already exists"
                
                # Check for existing email
                existing = session.query(Customer).filter_by(
                    email=email.lower()
                ).first()
                if existing:
                    return False, "Email already exists"
                
                # Create customer
                customer = Customer(
                    username=username.lower(),
                    email=email.lower(),
                    password_hash=generate_password_hash(password),
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number
                )
                session.add(customer)
                session.flush()
                
                return True, customer
                
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    @staticmethod
    def authenticate_customer(username_or_email, password):
        """
        Authenticate a customer
        
        Args:
            username_or_email (str): Username or email
            password (str): Password
            
        Returns:
            tuple: (success: bool, customer or error_message)
        """
        try:
            with get_db_session() as session:
                # Find customer by username or email
                customer = session.query(Customer).filter(
                    (Customer.username == username_or_email.lower()) |
                    (Customer.email == username_or_email.lower())
                ).first()
                
                if not customer:
                    return False, "Invalid credentials"
                
                if not customer.is_active:
                    return False, "Account is inactive"
                
                # Verify password
                if not check_password_hash(customer.password_hash, password):
                    return False, "Invalid credentials"
                
                # Update last login
                customer.last_login = datetime.now()
                
                return True, customer
                
        except Exception as e:
            return False, f"Authentication failed: {str(e)}"
    
    @staticmethod
    def authenticate_admin(username, password):
        """
        Authenticate an admin user
        
        Args:
            username (str): Admin username
            password (str): Password
            
        Returns:
            tuple: (success: bool, admin or error_message)
        """
        try:
            with get_db_session() as session:
                admin = session.query(AdminUser).filter_by(
                    username=username.lower()
                ).first()
                
                if not admin:
                    return False, "Invalid credentials"
                
                if not admin.is_active:
                    return False, "Admin account is inactive"
                
                # Verify password
                if not check_password_hash(admin.password_hash, password):
                    return False, "Invalid credentials"
                
                # Update last login
                admin.last_login = datetime.now()
                
                return True, admin
                
        except Exception as e:
            return False, f"Authentication failed: {str(e)}"
    
    @staticmethod
    def change_customer_password(customer_id, current_password, new_password):
        """
        Change customer password
        
        Args:
            customer_id (int): Customer ID
            current_password (str): Current password
            new_password (str): New password
            
        Returns:
            tuple: (success: bool, message)
        """
        # Validate new password
        is_valid, message = AuthService.validate_password_strength(new_password)
        if not is_valid:
            return False, message
        
        try:
            with get_db_session() as session:
                customer = session.query(Customer).filter_by(
                    customer_id=customer_id
                ).first()
                
                if not customer:
                    return False, "Customer not found"
                
                # Verify current password
                if not check_password_hash(customer.password_hash, current_password):
                    return False, "Current password is incorrect"
                
                # Update password
                customer.password_hash = generate_password_hash(new_password)
                
                return True, "Password changed successfully"
                
        except Exception as e:
            return False, f"Failed to change password: {str(e)}"
    
    @staticmethod
    def get_customer_by_id(customer_id):
        """
        Get customer by ID
        
        Args:
            customer_id (int): Customer ID
            
        Returns:
            Customer or None
        """
        try:
            with get_db_session() as session:
                return session.query(Customer).filter_by(
                    customer_id=customer_id
                ).first()
        except Exception:
            return None
    
    @staticmethod
    def get_admin_by_id(admin_id):
        """
        Get admin by ID
        
        Args:
            admin_id (int): Admin ID
            
        Returns:
            AdminUser or None
        """
        try:
            with get_db_session() as session:
                return session.query(AdminUser).filter_by(
                    admin_id=admin_id
                ).first()
        except Exception:
            return None
    
    @staticmethod
    def check_admin_permission(admin_id, permission):
        """
        Check if admin has specific permission
        
        Args:
            admin_id (int): Admin ID
            permission (str): Permission to check
            
        Returns:
            bool: True if has permission, False otherwise
        """
        try:
            with get_db_session() as session:
                admin = session.query(AdminUser).filter_by(
                    admin_id=admin_id
                ).first()
                
                if not admin:
                    return False
                
                return admin.has_permission(permission)
        except Exception:
            return False
    
    @staticmethod
    def update_customer_profile(customer_id, **kwargs):
        """
        Update customer profile
        
        Args:
            customer_id (int): Customer ID
            **kwargs: Fields to update (first_name, last_name, phone_number)
            
        Returns:
            tuple: (success: bool, customer or error_message)
        """
        try:
            with get_db_session() as session:
                customer = session.query(Customer).filter_by(
                    customer_id=customer_id
                ).first()
                
                if not customer:
                    return False, "Customer not found"
                
                # Update allowed fields
                allowed_fields = ['first_name', 'last_name', 'phone_number']
                for field in allowed_fields:
                    if field in kwargs:
                        setattr(customer, field, kwargs[field])
                
                return True, customer
                
        except Exception as e:
            return False, f"Failed to update profile: {str(e)}"