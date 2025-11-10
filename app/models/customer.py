"""
Customer Model  
Represents customers who can place orders
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app
from  .shopping_cart import ShoppingCart
from  .order import Order
from  .uploaded_file import UploadedFile


class Customer:
    """Customers table"""

    def __init__(self):
        self.conn = psycopg2.connect(
            current_app.config['SQLALCHEMY_DATABASE_URI'].replace(
                "postgresql+psycopg2", "postgresql"
            ),
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def __del__(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass

    # ---------------------
    # CREATE
    # ---------------------
    def create(self, username, email, password_hash, first_name, last_name, phone_number=None, is_active=True):
        sql = """
            INSERT INTO customers (
                username, email, password_hash, first_name, last_name, phone_number, is_active, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING customer_id;
        """
        now = datetime.utcnow()
        values = (username, email, password_hash, first_name, last_name, phone_number, is_active, now)
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.fetchone()["customer_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, customer_id):
        sql = "SELECT * FROM customers WHERE customer_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            customer = cur.fetchone()
            if customer:
                customer['shopping_carts'] = self.get_shopping_carts(customer_id)
                customer['orders'] = self.get_orders(customer_id)
                customer['uploaded_files'] = self.get_uploaded_files(customer_id)
            return customer

    def get_by_username(self, username):
        sql = "SELECT * FROM customers WHERE username = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, customer_id, **kwargs):
        updates = []
        values = []

        for key, value in kwargs.items():
            if key in ['username', 'email', 'password_hash', 'first_name', 'last_name', 'phone_number', 'is_active', 'last_login']:
                updates.append(f"{key} = %s")
                values.append(value)

        if not updates:
            return False

        sql = f"UPDATE customers SET {', '.join(updates)} WHERE customer_id = %s;"
        values.append(customer_id)
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, customer_id):
        sql = "DELETE FROM customers WHERE customer_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # RELATED OBJECTS
    # ---------------------
    def get_shopping_carts(self, customer_id):
        cart_model = ShoppingCart()
        return cart_model.get_by_customer(customer_id)

    def get_orders(self, customer_id):
        order_model = Order()
        return order_model.get_by_customer(customer_id)

    def get_uploaded_files(self, customer_id):
        uploaded_file_model = UploadedFile()
        return uploaded_file_model.get_by_customer(customer_id)

    # ---------------------
    # HELPERS
    # ---------------------
    def full_name(self, customer):
        return f"{customer['first_name']} {customer['last_name']}"

    def get_active_cart(self, customer):
        now = datetime.utcnow()
        for cart in customer.get('shopping_carts', []):
            if cart['expires_at'] and cart['expires_at'] > now:
                return cart
        return None

    def get_order_history(self, customer):
        return sorted(customer.get('orders', []), key=lambda x: x['created_at'], reverse=True)

    def get_total_spent(self, customer):
        return sum(order['total_amount'] for order in customer.get('orders', []) if order['order_status'] == 'completed')

    def get_order_count(self, customer):
        return len(customer.get('orders', []))
