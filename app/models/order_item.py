"""
app/models/order_item.py
Order Item Model  
Represents individual items in orders
"""

from app.database import get_cursor
from datetime import datetime  
 
from .order_item_customization import OrderItemCustomization


class OrderItem: 
    def __init__( self, order_item_id=None, order_id=None, product_id=None, quantity=1, unit_price=0.0, design_file_url=None,  subtotal=0.0, created_at=None ):


        self.order_item_id = order_item_id
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = float(unit_price)
        self.design_file_url = design_file_url
        self.subtotal = float(subtotal)
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        return {
            'order_item_id': self.order_item_id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'design_file_url': self.design_file_url,
            'subtotal': self.subtotal,
            'created_at': self.created_at.isoformat()
        }
    
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
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute(sql, (order_id, product_id, quantity, unit_price, design_file_url, subtotal, now))
             
            return cur.fetchone()["order_item_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, order_item_id):
        sql = "SELECT * FROM order_items WHERE order_item_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (order_item_id,))
            return cur.fetchone()

    def get_by_order(self, order_id):
        sql = "SELECT * FROM order_items WHERE order_id = %s;"
        with get_cursor(commit=False) as cur:
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
            with get_cursor(commit=False) as cur:
                cur.execute(sql_get, (order_item_id,))
                row = cur.fetchone()
                q = quantity if quantity is not None else row["quantity"]
                up = unit_price if unit_price is not None else row["unit_price"]
                updates.append("subtotal = %s")
                values.append(q * up)

        sql = f"UPDATE order_items SET {', '.join(updates)} WHERE order_item_id = %s;"
        values.append(order_item_id)

        with get_cursor() as cur:
            cur.execute(sql, tuple(values))
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, order_item_id):
        sql = "DELETE FROM order_items WHERE order_item_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (order_item_id,))
             
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def calculate_subtotal(self, quantity, unit_price):
        return float(quantity * unit_price)

    # Return all customizations for this order item
    def get_customizations(self, order_item_id): 
        customization_model = OrderItemCustomization()
        return customization_model.get_by_order_item(order_item_id)