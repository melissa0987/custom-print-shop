"""
app/models/category.py
Category Model  
Represents product categories
"""

from app.database import get_cursor
from datetime import datetime  
 
from  .product import Product


class Category:
    """Categories table for organizing products""" 

    def __init__( self, category_id=None, category_name=None, description=None, is_active=True, display_order=0, created_at=None, updated_at=None, created_by=None,  updated_by=None):
        self.category_id = category_id
        self.category_name = category_name
        self.description = description
        self.is_active = is_active
        self.display_order = display_order
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.created_by = created_by
        self.updated_by = updated_by

    def to_dict(self):
        return {
            'category_id': self.category_id,
            'category_name': self.category_name,
            'description': self.description,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }

    # ---------------------
    # CREATE
    # ---------------------
    def create(self, category_name, description=None, is_active=True, display_order=0, created_by=None):
        sql = """
            INSERT INTO categories (
                category_name, description, is_active, display_order, created_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING category_id;
        """
        now = datetime.now()
        values = (category_name, description, is_active, display_order, created_by, now, now)
        with get_cursor() as cur:
            cur.execute(sql, values)
             
            return cur.fetchone()["category_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, category_id):
        sql = "SELECT * FROM categories WHERE category_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (category_id,))
            category = cur.fetchone()
            if category:
                category['products'] = self.get_products(category_id)
            return category

    def get_all(self):
        sql = "SELECT * FROM categories ORDER BY display_order ASC;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql)
            categories = cur.fetchall()
            for cat in categories:
                cat['products'] = self.get_products(cat['category_id'])
            return categories

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, category_id, **kwargs):
        updates = []
        values = []

        for key, value in kwargs.items():
            if key in ['category_name', 'description', 'is_active', 'display_order', 'updated_by']:
                updates.append(f"{key} = %s")
                values.append(value)

        if not updates:
            return False

        # Update timestamp
        updates.append("updated_at = %s")
        values.append(datetime.now())
        values.append(category_id)

        sql = f"UPDATE categories SET {', '.join(updates)} WHERE category_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, tuple(values))
             
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, category_id):
        sql = "DELETE FROM categories WHERE category_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (category_id,))
             
            return cur.rowcount > 0

    # ---------------------
    # RELATED PRODUCTS
    # ---------------------
    # Fetch products for this category
    def get_products(self, category_id): 
        product_model = Product()
        return product_model.get_by_category(category_id)

    # Get all active products in this category"
    def get_active_products(self, category_id): 
        return [p for p in self.get_products(category_id) if p['is_active']]

    # otal products in this category
    def get_product_count(self, category_id): 
        return len(self.get_products(category_id))

    # Number of active products in this category
    def get_active_product_count(self, category_id): 
        return len(self.get_active_products(category_id))
