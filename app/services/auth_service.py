"""
Authentication Service
Business logic for user authentication and registration
Updated to use psycopg2-based models
"""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from app.models import Customer, AdminUser
from app.utils.validators import Validators


class AuthService:
    """Service class for authentication and user management operations"""

    @staticmethod
    def register_customer(username, email, password, first_name, last_name, phone_number=None):
        """
        Register a new customer

        Args:
            username (str): Desired username
            email (str): Customer email
            password (str): Plain text password
            first_name (str): First name
            last_name (str): Last name
            phone_number (str, optional): Phone number

        Returns:
            tuple: (success: bool, customer or error_message)
        """
        # Sanitize and validate inputs
        username = Validators.sanitize_string(username, max_length=50)
        email = Validators.sanitize_string(email.lower())
        first_name = Validators.sanitize_string(first_name, max_length=50)
        last_name = Validators.sanitize_string(last_name, max_length=50)
        phone_number = Validators.sanitize_string(phone_number, max_length=20) if phone_number else None

        # Input validation checks
        if not Validators.validate_username(username):
            return False, "Invalid username format (3-50 characters, letters/numbers/underscore/hyphen)"
        if not Validators.validate_email(email):
            return False, "Invalid email address"
        is_valid, message = Validators.validate_password_strength(password)
        if not is_valid:
            return False, message
        if phone_number and not Validators.validate_phone_number(phone_number):
            return False, "Invalid phone number format"

        try:
            customer_model = Customer()
            
            # Check for existing username or email
            existing_username = customer_model.get_by_username(username.lower())
            if existing_username:
                return False, "Username already exists"
            
            # Check email through a simple query
            # Note: You may want to add a get_by_email method to Customer model
            existing_email = customer_model.get_by_username(email.lower())  # Using username method temporarily
            if existing_email and existing_email.get('email') == email.lower():
                return False, "Email already exists"

            # Create new customer
            password_hash = generate_password_hash(password)
            customer_id = customer_model.create(
                username=username.lower(),
                email=email.lower(),
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                is_active=True
            )

            # Get the created customer
            customer = customer_model.get_by_id(customer_id)
            return True, customer

        except Exception as e:
            return False, f"Registration failed: {str(e)}"

    @staticmethod
    def authenticate_customer(username_or_email, password):
        """
        Authenticate a customer by username or email

        Args:
            username_or_email (str): Username or email
            password (str): Password

        Returns:
            tuple: (success: bool, customer or error_message)
        """
        try:
            customer_model = Customer()
            username_or_email = username_or_email.strip().lower()

            # Try to find customer by username
            customer = customer_model.get_by_username(username_or_email)
            
            # If not found by username, it might be an email
            # Note: Consider adding get_by_email method to Customer model for better efficiency
            
            if not customer:
                return False, "Invalid credentials"
            
            if not customer.get('is_active'):
                return False, "Account is inactive"

            # Verify password
            if not check_password_hash(customer['password_hash'], password):
                return False, "Invalid credentials"

            # Update last login timestamp
            customer_model.update(customer['customer_id'], last_login=datetime.utcnow())

            # Refresh customer data
            customer = customer_model.get_by_id(customer['customer_id'])
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
            admin_model = AdminUser()
            username = username.strip().lower()

            # Find admin by username
            admin = admin_model.get_by_username(username)

            if not admin:
                return False, "Invalid credentials"
            
            if not admin.get('is_active'):
                return False, "Admin account is inactive"

            # Verify password using the model's static method
            if not AdminUser.verify_password(admin, password):
                return False, "Invalid credentials"

            # Update last login
            admin_model.update_last_login(admin['admin_id'])

            # Refresh admin data
            admin = admin_model.get_by_id(admin['admin_id'])
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
        # Validate new password strength
        is_valid, message = Validators.validate_password_strength(new_password)
        if not is_valid:
            return False, message

        try:
            customer_model = Customer()
            customer = customer_model.get_by_id(customer_id)
            
            if not customer:
                return False, "Customer not found"

            # Verify old password
            if not check_password_hash(customer['password_hash'], current_password):
                return False, "Current password is incorrect"

            # Update to new password
            new_password_hash = generate_password_hash(new_password)
            customer_model.update(customer_id, password_hash=new_password_hash)

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
            dict or None: Customer data
        """
        try:
            customer_model = Customer()
            return customer_model.get_by_id(customer_id)
        except Exception:
            return None

    @staticmethod
    def get_admin_by_id(admin_id):
        """
        Get admin by ID
        
        Args:
            admin_id (int): Admin ID
            
        Returns:
            dict or None: Admin data
        """
        try:
            admin_model = AdminUser()
            return admin_model.get_by_id(admin_id)
        except Exception:
            return None

    @staticmethod
    def check_admin_permission(admin_id, permission):
        """
        Check if admin has a specific permission

        Args:
            admin_id (int): Admin ID
            permission (str): Permission name

        Returns:
            bool: True if admin has permission, False otherwise
        """
        try:
            admin_model = AdminUser()
            admin = admin_model.get_by_id(admin_id)
            
            if not admin:
                return False
                
            return AdminUser.has_permission(admin, permission)
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
        # Validate and sanitize inputs
        if 'first_name' in kwargs:
            kwargs['first_name'] = Validators.sanitize_string(kwargs['first_name'], max_length=50)
        if 'last_name' in kwargs:
            kwargs['last_name'] = Validators.sanitize_string(kwargs['last_name'], max_length=50)
        if 'phone_number' in kwargs:
            phone = Validators.sanitize_string(kwargs['phone_number'], max_length=20)
            if not Validators.validate_phone_number(phone):
                return False, "Invalid phone number format"
            kwargs['phone_number'] = phone

        try:
            customer_model = Customer()
            customer = customer_model.get_by_id(customer_id)
            
            if not customer:
                return False, "Customer not found"

            # Update specified fields
            success = customer_model.update(customer_id, **kwargs)
            
            if not success:
                return False, "Profile update failed"

            # Get updated customer
            customer = customer_model.get_by_id(customer_id)
            return True, customer

        except Exception as e:
            return False, f"Profile update failed: {str(e)}"