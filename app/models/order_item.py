"""
Order Item Model  
Represents individual items in orders
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app
from .order_item_customization import OrderItemCustomization


class OrderItem:
    """Order items table"""

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
    def create(self, order_id, product_id, quantity, unit_price, design_file_url=None):
        subtotal = quantity * unit_price
        sql = """
            INSERT INTO order_items (
                order_id, product_id, quantity, unit_price, design_file_url, subtotal, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING order_item_id;
        """
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id, product_id, quantity, unit_price, design_file_url, subtotal, now))
            self.conn.commit()
            return cur.fetchone()["order_item_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, order_item_id):
        sql = "SELECT * FROM order_items WHERE order_item_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_item_id,))
            return cur.fetchone()

    def get_by_order(self, order_id):
        sql = "SELECT * FROM order_items WHERE order_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, order_item_id, quantity=None, unit_price=None, design_file_url=None):
        updates = []
        values = []

        if quantity is not None:
            updates.append("quantity = %s")
            values.append(quantity)
        if unit_price is not None:
            updates.append("unit_price = %s")
            values.append(unit_price)
        if design_file_url is not None:
            updates.append("design_file_url = %s")
            values.append(design_file_url)
        if not updates:
            return False

        # Recalculate subtotal if quantity or unit_price changed
        if quantity is not None or unit_price is not None:
            sql_get = "SELECT quantity, unit_price FROM order_items WHERE order_item_id = %s;"
            with self.conn.cursor() as cur:
                cur.execute(sql_get, (order_item_id,))
                row = cur.fetchone()
                q = quantity if quantity is not None else row["quantity"]
                up = unit_price if unit_price is not None else row["unit_price"]
                updates.append("subtotal = %s")
                values.append(q * up)

        sql = f"UPDATE order_items SET {', '.join(updates)} WHERE order_item_id = %s;"
        values.append(order_item_id)

        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, order_item_id):
        sql = "DELETE FROM order_items WHERE order_item_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_item_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def calculate_subtotal(self, quantity, unit_price):
        return float(quantity * unit_price)

    def get_customizations(self, order_item_id):
        """Return all customizations for this order item"""
        customization_model = OrderItemCustomization()
        return customization_model.get_by_order_item(order_item_id)
