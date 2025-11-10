"""
Shopping Cart Model  
Represents shopping carts for customers and guest users
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from flask import current_app


class ShoppingCart:
    """Shopping carts table"""

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
    def create(self, customer_id=None, session_id=None, expires_at=None):
        if (customer_id is None and session_id is None) or (customer_id and session_id):
            raise ValueError("Cart must have either a customer_id or session_id, not both.")

        expires_at = expires_at or (datetime.utcnow() + timedelta(days=30))
        now = datetime.utcnow()

        sql = """
            INSERT INTO shopping_carts (customer_id, session_id, created_at, updated_at, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING shopping_cart_id;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id, session_id, now, now, expires_at))
            self.conn.commit()
            return cur.fetchone()["shopping_cart_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, cart_id):
        sql = "SELECT * FROM shopping_carts WHERE shopping_cart_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM shopping_carts WHERE customer_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()

    def get_by_session(self, session_id):
        sql = "SELECT * FROM shopping_carts WHERE session_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (session_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update_expires(self, cart_id, expires_at):
        sql = "UPDATE shopping_carts SET expires_at = %s, updated_at = %s WHERE shopping_cart_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (expires_at, datetime.utcnow(), cart_id))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, cart_id):
        sql = "DELETE FROM shopping_carts WHERE shopping_cart_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def is_expired(self, cart):
        """Check if a cart record is expired"""
        return cart.get("expires_at") and cart["expires_at"] < datetime.utcnow()

    def get_total_items(self, cart_id):
        """Get total number of items in cart"""
        sql = "SELECT COUNT(*) AS total_items FROM cart_items WHERE shopping_cart_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()["total_items"]

    def get_total_quantity(self, cart_id):
        """Get total quantity of all items in cart"""
        sql = "SELECT COALESCE(SUM(quantity),0) AS total_quantity FROM cart_items WHERE shopping_cart_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()["total_quantity"]

    def calculate_total(self, cart_id):
        """Calculate total price of all items in cart"""
        sql = """
            SELECT COALESCE(SUM(ci.quantity * p.base_price), 0) AS total
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.shopping_cart_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_id,))
            return float(cur.fetchone()["total"])
