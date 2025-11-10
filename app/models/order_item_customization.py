"""
Order Item Customization Model  
Represents customizations for order items
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app 


class OrderItemCustomization:
    """Order item customizations table"""

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
    def create(self, order_item_id, customization_key, customization_value):
        sql = """
            INSERT INTO order_item_customizations (
                order_item_id, customization_key, customization_value, created_at
            ) VALUES (%s, %s, %s, %s)
            RETURNING customization_id;
        """
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_item_id, customization_key, customization_value, now))
            self.conn.commit()
            return cur.fetchone()["customization_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, customization_id):
        sql = "SELECT * FROM order_item_customizations WHERE customization_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customization_id,))
            return cur.fetchone()

    def get_by_order_item(self, order_item_id):
        sql = "SELECT * FROM order_item_customizations WHERE order_item_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_item_id,))
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

        sql = f"UPDATE order_item_customizations SET {', '.join(updates)} WHERE customization_id = %s;"
        values.append(customization_id)

        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, customization_id):
        sql = "DELETE FROM order_item_customizations WHERE customization_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customization_id,))
            self.conn.commit()
            return cur.rowcount > 0
