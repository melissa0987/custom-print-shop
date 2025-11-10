"""
Admin User Model  
Represents administrative users with role-based access control
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash


class AdminUser:
    """Handles admin user operations using psycopg2"""

    def __init__(self):
        self.conn = psycopg2.connect(
            current_app.config['SQLALCHEMY_DATABASE_URI'].replace(
                "postgresql+psycopg2", "postgresql"
            ),
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def __del__(self):
        """Ensure connection closes"""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass

    # ---------------------
    # CREATE
    # ---------------------
    def create(self, username, email, password, first_name, last_name,
               role='staff', is_active=True, created_by=None):
        """
        Create a new admin user
        """
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
            role, is_active, created_by, datetime.utcnow()
        )
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.fetchone()["admin_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, admin_id):
        sql = "SELECT * FROM admin_users WHERE admin_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (admin_id,))
            return cur.fetchone()

    def get_by_username(self, username):
        sql = "SELECT * FROM admin_users WHERE username = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()

    def get_all(self, limit=50):
        sql = "SELECT * FROM admin_users ORDER BY created_at DESC LIMIT %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update_last_login(self, admin_id):
        sql = "UPDATE admin_users SET last_login = %s WHERE admin_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (datetime.utcnow(), admin_id))
            self.conn.commit()
            return cur.rowcount > 0

    def update_password(self, admin_id, new_password):
        password_hash = generate_password_hash(new_password)
        sql = "UPDATE admin_users SET password_hash = %s WHERE admin_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (password_hash, admin_id))
            self.conn.commit()
            return cur.rowcount > 0

    def update_status(self, admin_id, is_active):
        sql = "UPDATE admin_users SET is_active = %s WHERE admin_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (is_active, admin_id))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, admin_id):
        sql = "DELETE FROM admin_users WHERE admin_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (admin_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # UTILITY
    # ---------------------
    @staticmethod
    def full_name(user_record):
        """Return full name from a database record"""
        if user_record:
            return f"{user_record['first_name']} {user_record['last_name']}"
        return "Unknown"

    @staticmethod
    def verify_password(user_record, password):
        """Verify password hash"""
        if not user_record:
            return False
        return check_password_hash(user_record['password_hash'], password)

    @staticmethod
    def has_permission(user_record, action):
        """
        Check if admin has permission for an action
        """
        if not user_record or not user_record['is_active']:
            return False

        role = user_record['role']

        if role == 'super_admin':
            return True

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

        if role == 'admin':
            return action in admin_permissions
        elif role == 'staff':
            return action in staff_permissions

        return False
