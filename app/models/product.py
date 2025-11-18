"""
app/models/product.py
Product Model  
Represents products available for custom printing
"""

from app.database import get_cursor
from datetime import datetime  
 


class Product: 
    def __init__( self,  product_id=None, category_id=None, product_name=None, 
                 description=None, base_price=0.0, is_active=True, 
                 created_at=None,  updated_at=None, created_by=None, 
                 updated_by=None  ):

        self.product_id = product_id
        self.category_id = category_id
        self.product_name = product_name
        self.description = description
        self.base_price = float(base_price)
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.created_by = created_by
        self.updated_by = updated_by

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'category_id': self.category_id,
            'product_name': self.product_name,
            'description': self.description,
            'base_price': self.base_price,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }

    # ---------------------
    # CREATE
    # ---------------------
    def create(self, category_id, product_name, base_price, description=None,
               is_active=True, created_by=None, updated_by=None):
        if base_price < 0:
            raise ValueError("base_price must be >= 0")

        sql = """
            INSERT INTO products (
                category_id, product_name, description, base_price,
                is_active, created_by, updated_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING product_id;
        """
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute(sql, (
                category_id, product_name, description, base_price,
                is_active, created_by, updated_by, now, now
            )) 
            return cur.fetchone()["product_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, product_id):
        sql = "SELECT * FROM products WHERE product_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()

    def get_all(self, active_only=True):
        sql = "SELECT * FROM products"
        if active_only:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY product_name ASC;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql)
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, product_id, **kwargs):
        allowed_fields = ['category_id', 'product_name', 'description', 'base_price',
                          'is_active', 'updated_by']
        updates = []
        values = []

        for key, val in kwargs.items():
            if key in allowed_fields:
                if key == 'base_price' and val < 0:
                    raise ValueError("base_price must be >= 0")
                updates.append(f"{key} = %s")
                values.append(val)

        if not updates:
            return False

        values.append(datetime.now()) 
        values.append(product_id)  

        sql = f"""
            UPDATE products
            SET {', '.join(updates)}, updated_at = %s
            WHERE product_id = %s;
        """
        with get_cursor() as cur:
            cur.execute(sql, values) 
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, product_id):
        sql = "DELETE FROM products WHERE product_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (product_id,)) 
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    # Return total number of order items for this product
    def get_total_orders(self, product_id): 
        sql = "SELECT COUNT(*) FROM order_items WHERE product_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()["count"]


    # Return total quantity sold
    def get_total_quantity_sold(self, product_id): 
        sql = "SELECT COALESCE(SUM(quantity),0) AS total FROM order_items WHERE product_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()["total"]

    # Return total revenue generated
    def get_total_revenue(self, product_id): 
        sql = "SELECT COALESCE(SUM(subtotal),0) AS revenue FROM order_items WHERE product_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (product_id,))
            return float(cur.fetchone()["revenue"])
        
    # Return all products in a category 
    def get_by_category(self, category_id): 
        sql = "SELECT * FROM products WHERE category_id = %s ORDER BY product_name ASC;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (category_id,))
            return cur.fetchall()
