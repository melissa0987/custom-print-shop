"""
app/models/cart_item.py
Cart Item Model  
Represents individual items in shopping carts
"""

from app.database import get_cursor
from datetime import datetime  
 
from .cart_item_customization import CartItemCustomization
from .uploaded_file import UploadedFile


class CartItem: 
    def __init__( self, cart_item_id=None, shopping_cart_id=None, product_id=None, quantity=1, design_file_url=None, added_at=None, updated_at=None ):
        
        self.cart_item_id = cart_item_id
        self.shopping_cart_id = shopping_cart_id
        self.product_id = product_id
        self.quantity = quantity
        self.design_file_url = design_file_url
        self.added_at = added_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            'cart_item_id': self.cart_item_id,
            'shopping_cart_id': self.shopping_cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'design_file_url': self.design_file_url,
            'added_at': self.added_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    # ---------------------
    # CREATE
    # ---------------------
    def create(self, shopping_cart_id, product_id, quantity, design_file_url=None):
        sql = """
            INSERT INTO cart_items (
                shopping_cart_id, product_id, quantity, design_file_url, added_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING cart_item_id;
        """
        now = datetime.now()
        values = (shopping_cart_id, product_id, quantity, design_file_url, now, now)
        with get_cursor() as cur:
            cur.execute(sql, values)
             
            return cur.fetchone()["cart_item_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, cart_item_id):
        sql = "SELECT * FROM cart_items WHERE cart_item_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_item_id,))
            item = cur.fetchone()
            if item:
                # Fetch customizations
                cust_model = CartItemCustomization()
                item['customizations'] = cust_model.get_by_cart_item(cart_item_id)
                # Fetch uploaded files
                file_model = UploadedFile()
                item['uploaded_files'] = file_model.get_by_cart_item(cart_item_id)
            return item

    def get_by_cart(self, shopping_cart_id):
        sql = "SELECT * FROM cart_items WHERE shopping_cart_id = %s ORDER BY added_at ASC;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (shopping_cart_id,))
            items = cur.fetchall()
            cust_model = CartItemCustomization()
            file_model = UploadedFile()
            for item in items:
                item['customizations'] = cust_model.get_by_cart_item(item['cart_item_id'])
                item['uploaded_files'] = file_model.get_by_cart_item(item['cart_item_id'])
            return items

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, cart_item_id, quantity=None, design_file_url=None):
        updates = []
        values = []

        if quantity is not None:
            updates.append("quantity = %s")
            values.append(quantity)
        if design_file_url is not None:
            updates.append("design_file_url = %s")
            values.append(design_file_url)

        if not updates:
            return False

        # Update timestamp
        updates.append("updated_at = %s")
        values.append(datetime.now())
        values.append(cart_item_id)

        sql = f"UPDATE cart_items SET {', '.join(updates)} WHERE cart_item_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, tuple(values))
             
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, cart_item_id):
        sql = "DELETE FROM cart_items WHERE cart_item_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (cart_item_id,))
             
            return cur.rowcount > 0

    # ---------------------
    # UTILITY METHODS
    # ---------------------

    # Calculate line total: quantity * product price
    def get_line_total(self, cart_item): 
        return float(cart_item['quantity'] * cart_item['product']['base_price'])

    def add_customization(self, cart_item_id, key, value):
        """Add a customization to this cart item"""
        cust_model = CartItemCustomization()
        return cust_model.create(cart_item_id, key, value)
