"""
app/models/order_item_customization.py
Order Item Customization Model  
Represents customizations for order items
"""

from app.database import get_cursor
from datetime import datetime  
 


class OrderItemCustomization: 
    def __init__(
        self,
        customization_id=None,
        order_item_id=None,
        customization_key=None,
        customization_value=None,
        created_at=None
    ):
        self.customization_id = customization_id
        self.order_item_id = order_item_id
        self.customization_key = customization_key
        self.customization_value = customization_value
        self.created_at = created_at or datetime.now() 

    def to_dict(self):
        return {
            'customization_id': self.customization_id,
            'order_item_id': self.order_item_id,
            'customization_key': self.customization_key,
            'customization_value': self.customization_value,
            'created_at': self.created_at.isoformat()
        }

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
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute(sql, (order_item_id, customization_key, customization_value, now)) 
            return cur.fetchone()["customization_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, customization_id):
        sql = "SELECT * FROM order_item_customizations WHERE customization_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (customization_id,))
            return cur.fetchone()

    def get_by_order_item(self, order_item_id):
        sql = "SELECT * FROM order_item_customizations WHERE order_item_id = %s;"
        with get_cursor(commit=False) as cur:
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

        with get_cursor() as cur:
            cur.execute(sql, tuple(values))
             
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, customization_id):
        sql = "DELETE FROM order_item_customizations WHERE customization_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (customization_id,))
             
            return cur.rowcount > 0
