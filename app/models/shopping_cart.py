"""
app/models/shopping_cart.py
Shopping Cart Model  
Represents shopping carts for customers and guest users
"""

from app.database import get_cursor
from datetime import datetime, timedelta
 
class ShoppingCart: 
    def __init__( self, shopping_cart_id=None, customer_id=None, session_id=None, created_at=None, updated_at=None, expires_at=None  ):

        self.shopping_cart_id = shopping_cart_id
        self.customer_id = customer_id
        self.session_id = session_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.expires_at = expires_at or (self.created_at + timedelta(days=30))

    def to_dict(self):
        return {
            'shopping_cart_id': self.shopping_cart_id,
            'customer_id': self.customer_id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    # ---------------------
    # CREATE
    # ---------------------
    def create(self, customer_id=None, session_id=None, expires_at=None):
        if (customer_id is None and session_id is None) or (customer_id and session_id):
            raise ValueError("Cart must have either a customer_id or session_id, not both.")

        expires_at = expires_at or (datetime.now() + timedelta(days=30))
        now = datetime.now()

        sql = """
            INSERT INTO shopping_carts (customer_id, session_id, created_at, updated_at, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING shopping_cart_id;
        """
        with get_cursor() as cur:
            cur.execute(sql, (customer_id, session_id, now, now, expires_at))
            
            return cur.fetchone()["shopping_cart_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, cart_id):
        sql = "SELECT * FROM shopping_carts WHERE shopping_cart_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM shopping_carts WHERE customer_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()

    def get_by_session(self, session_id):
        sql = "SELECT * FROM shopping_carts WHERE session_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (session_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update_expires(self, cart_id, expires_at):
        sql = "UPDATE shopping_carts SET expires_at = %s, updated_at = %s WHERE shopping_cart_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (expires_at, datetime.now(), cart_id))
            
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, cart_id):
        sql = "DELETE FROM shopping_carts WHERE shopping_cart_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (cart_id,))
            
            return cur.rowcount > 0
        
    def get_all_expired(self):
        """Get all expired carts"""
        sql = "SELECT * FROM shopping_carts WHERE expires_at < %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (datetime.now(),))
            return cur.fetchall()

    def delete_expired_carts(self):
        """Delete all expired carts and return count"""
        sql = "DELETE FROM shopping_carts WHERE expires_at < %s RETURNING shopping_cart_id;"
        with get_cursor() as cur:
            cur.execute(sql, (datetime.now(),))
            return cur.rowcount

    # ---------------------
    # HELPERS
    # ---------------------
    # Check if a cart record is expired"
    def is_expired(self, cart): 
        return cart.get("expires_at") and cart["expires_at"] < datetime.now()

    # Get total number of items in cart
    def get_total_items(self, cart_id): 
        sql = "SELECT COUNT(*) AS total_items FROM cart_items WHERE shopping_cart_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()["total_items"]

    # Get total quantity of all items in cart 
    def get_total_quantity(self, cart_id): 
        sql = "SELECT COALESCE(SUM(quantity),0) AS total_quantity FROM cart_items WHERE shopping_cart_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_id,))
            return cur.fetchone()["total_quantity"]


    # Calculate total price of all items in cart
    def calculate_total(self, cart_id): 
        sql = """
            SELECT COALESCE(SUM(ci.quantity * p.base_price), 0) AS total
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.shopping_cart_id = %s;
        """
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_id,))
            return float(cur.fetchone()["total"])
