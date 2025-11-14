"""
app/models/admin_user.py
Admin User Model  
Represents administrative users with role-based access control
"""

from app.database import get_cursor
from datetime import datetime 
 
from werkzeug.security import generate_password_hash, check_password_hash


class AdminUser: 
    
    def __init__(self, admin_id=None, username=None, password_hash=None, email=None, first_name=None, last_name=None, role='staff',  is_active=True, created_at=None, last_login=None, created_by=None):
        self.admin_id = admin_id
        self.username = username
        self.password_hash = password_hash   
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.is_active = is_active
        self.created_at = datetime.now()
        self.last_login = last_login
        self.created_by = created_by

    def to_dict(self, include_sensitive=False): 
        data = {
            'admin_id': self.admin_id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_by': self.created_by,
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data

    # ---------------------
    # CREATE
    # ---------------------
    # Create a new admin user
    def create(self, username, email, password, first_name, last_name,
               role='staff', is_active=True, created_by=None):
        
        password_hash = generate_password_hash(password)
        sql = """
            INSERT INTO admin_users (
                username, email, password_hash, first_name, last_name,
                role, is_active, created_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING admin_id;
        """
        values = (
            username, email, password_hash, first_name, last_name,
            role, is_active, created_by, datetime.now())
        
        with get_cursor() as cur:
            cur.execute(sql, values)
            return cur.fetchone()["admin_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, admin_id):
        sql = "SELECT * FROM admin_users WHERE admin_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (admin_id,))
            return cur.fetchone()

    def get_by_username(self, username):
        sql = "SELECT * FROM admin_users WHERE username = %s ;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()
    
    def get_by_email(self, email):
        sql = "SELECT * FROM admin_users WHERE email = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (email,))
            return cur.fetchone()
        

    def get_all(self, limit=50):
        sql = "SELECT * FROM admin_users ORDER BY created_at DESC LIMIT %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update_last_login(self, admin_id):
        sql = "UPDATE admin_users SET last_login = %s WHERE admin_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (datetime.now(), admin_id))
            return cur.rowcount > 0

    def update_password(self, admin_id, new_password):
        password_hash = generate_password_hash(new_password)
        sql = "UPDATE admin_users SET password_hash = %s WHERE admin_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (password_hash, admin_id))
             
            return cur.rowcount > 0

    def update_status(self, admin_id, is_active):
        sql = "UPDATE admin_users SET is_active = %s WHERE admin_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (is_active, admin_id))
             
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, admin_id):
        sql = "DELETE FROM admin_users WHERE admin_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (admin_id,))
             
            return cur.rowcount > 0

    # ---------------------
    # UTILITY
    # ---------------------
    @staticmethod
    # Return full name from a database record
    def full_name(user_record): 
        if user_record:
            return f"{user_record['first_name']} {user_record['last_name']}"
        return "Unknown"

    # Verify password hash
    @staticmethod
    def verify_password(user_record, password): 
        if not user_record:
            return False
        return check_password_hash(user_record['password_hash'], password)

    # Check if admin has permission for an action
    @staticmethod
    def has_permission(user_record, action):
        
        if not user_record or not user_record['is_active']:
            return False

        role = user_record['role']

        if role == 'super_admin':
            return True

        admin_permissions = [
            'view_orders', 'update_order_status', 'view_customers',
            'view_products', 'add_product', 'update_product',
            'view_categories', 'add_category', 'update_category',
            'view_staff', 'view_reports', 'view_dashboard'
        ]

        staff_permissions = [
            'view_orders', 'update_order_status',
            'view_customers', 'view_products', 'view_categories',
            'view_dashboard' 
        ]

        

        if role == 'admin':
            return action in admin_permissions
        elif role == 'staff':
            return action in staff_permissions
        

        return False


    def get_permissions(self, admin_id):
        """
        Return a list of permission strings for the given admin user.
        """
        user = self.get_by_id(admin_id)
        if not user or not user.get('is_active', True):
            return []

        role = user.get('role', 'staff')

        admin_permissions = [
            'view_orders', 'update_order_status', 'view_customers',
            'view_products', 'add_product', 'update_product',
            'view_categories', 'add_category', 'update_category',
            'view_staff', 'view_reports'
        ]

        staff_permissions = [
            'view_orders', 'update_order_status',
            'view_customers', 'view_products', 'view_categories'
        ]

        if role == 'Admin':
            return admin_permissions  # super_admin gets all
        elif role == 'Administrator':
            return admin_permissions
        elif role == 'Staff':
            return staff_permissions

        return []