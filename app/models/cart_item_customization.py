"""
Cart Item Customization Model  
Represents customizations for cart items (e.g., size, color, print location)
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class CartItemCustomization:
    """Handles cart item customizations using psycopg2"""

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
    def create(self, cart_item_id, customization_key, customization_value):
        sql = """
            INSERT INTO cart_item_customizations (
                cart_item_id, customization_key, customization_value, created_at
            ) VALUES (%s, %s, %s, %s)
            RETURNING customization_id;
        """
        values = (cart_item_id, customization_key, customization_value, datetime.utcnow())
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.fetchone()["customization_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, customization_id):
        sql = "SELECT * FROM cart_item_customizations WHERE customization_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customization_id,))
            return cur.fetchone()

    def get_by_cart_item(self, cart_item_id):
        sql = """
            SELECT * FROM cart_item_customizations
            WHERE cart_item_id = %s
            ORDER BY created_at ASC;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_item_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, customization_id, customization_key=None, customization_value=None):
        updates = []
        values = []

        if customization_key is not None:
            updates.append("customization_key = %s")
            values.append(customization_key)

        if customization_value is not None:
            updates.append("customization_value = %s")
            values.append(customization_value)

        if not updates:
            return False

        values.append(customization_id)
        sql = f"""
            UPDATE cart_item_customizations
            SET {', '.join(updates)}
            WHERE customization_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, customization_id):
        sql = "DELETE FROM cart_item_customizations WHERE customization_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customization_id,))
            self.conn.commit()
            return cur.rowcount > 0
