"""
Authentication Service
Business logic for user authentication and registration
"""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

from app.database import get_db_session
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
        # --- Sanitize and validate inputs ---
        username = Validators.sanitize_string(username, max_length=50)
        email = Validators.sanitize_string(email.lower())
        first_name = Validators.sanitize_string(first_name, max_length=50)
        last_name = Validators.sanitize_string(last_name, max_length=50)
        phone_number = Validators.sanitize_string(phone_number, max_length=20) if phone_number else None

        # --- Input validation checks ---
        if not Validators.validate_username(username):
            return False, "Invalid username format (3–50 characters, letters/numbers/underscore/hyphen)"
        if not Validators.validate_email(email):
            return False, "Invalid email address"
        is_valid, message = Validators.validate_password_strength(password)
        if not is_valid:
            return False, message
        if phone_number and not Validators.validate_phone_number(phone_number):
            return False, "Invalid phone number format"

        try:
            with get_db_session() as session:
                # --- Prevent duplicate accounts ---
                if session.query(Customer).filter(
                    (Customer.username == username.lower()) | (Customer.email == email.lower())
                ).first():
                    return False, "Account already exists"

                # --- Create and persist new customer ---
                customer = Customer(
                    username=username.lower(),
                    email=email.lower(),
                    password_hash=generate_password_hash(password),
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number
                )
                session.add(customer)
                session.commit()  # Save to database

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
            with get_db_session() as session:
                # --- Normalize input ---
                username_or_email = username_or_email.strip().lower()

                # --- Find customer by username or email ---
                customer = session.query(Customer).filter(
                    (Customer.username == username_or_email) | (Customer.email == username_or_email)
                ).first()

                if not customer:
                    return False, "Invalid credentials"
                if not customer.is_active:
                    return False, "Account is inactive"

                # --- Verify password ---
                if not check_password_hash(customer.password_hash, password):
                    return False, "Invalid credentials"

                # --- Update last login timestamp ---
                customer.last_login = datetime.now(timezone.utc)
                session.commit()

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
                # --- Normalize input ---
                username = username.strip().lower()

                # --- Find admin by username ---
                admin = session.query(AdminUser).filter_by(username=username).first()

                if not admin:
                    return False, "Invalid credentials"
                if not admin.is_active:
                    return False, "Admin account is inactive"

                # --- Verify password ---
                if not check_password_hash(admin.password_hash, password):
                    return False, "Invalid credentials"

                # --- Update last login ---
                admin.last_login = datetime.now(timezone.utc)
                session.commit()

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
        # --- Validate new password strength ---
        is_valid, message = Validators.validate_password_strength(new_password)
        if not is_valid:
            return False, message

        try:
            with get_db_session() as session:
                # --- Retrieve customer ---
                customer = session.query(Customer).filter_by(customer_id=customer_id).first()
                if not customer:
                    return False, "Customer not found"

                # --- Verify old password ---
                if not check_password_hash(customer.password_hash, current_password):
                    return False, "Current password is incorrect"

                # --- Update to new password ---
                customer.password_hash = generate_password_hash(new_password)
                session.commit()

                return True, "Password changed successfully"

        except Exception as e:
            return False, f"Failed to change password: {str(e)}"

     
    @staticmethod
    def get_customer_by_id(customer_id):
        """
        Get customer by ID
        """
        try:
            with get_db_session() as session:
                return session.query(Customer).filter_by(customer_id=customer_id).first()
        except Exception:
            return None

     
    @staticmethod
    def get_admin_by_id(admin_id):
        """
        Get admin by ID
        """
        try:
            with get_db_session() as session:
                return session.query(AdminUser).filter_by(admin_id=admin_id).first()
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
            with get_db_session() as session:
                admin = session.query(AdminUser).filter_by(admin_id=admin_id).first()
                return admin.has_permission(permission) if admin else False
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
        # --- Validate and sanitize inputs ---
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
            with get_db_session() as session:
                # --- Retrieve customer record ---
                customer = session.query(Customer).filter_by(customer_id=customer_id).first()
                if not customer:
                    return False, "Customer not found"

                # --- Update specified fields dynamically ---
                for key, value in kwargs.items():
                    setattr(customer, key, value)

                session.commit()
                session.refresh(customer)  # Refresh object with new DB state

                return True, customer

        except Exception as e:
            return False, f"Profile update failed: {str(e)}"
