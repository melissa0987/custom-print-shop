"""
Category Model  
Represents product categories
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app
from  .product import Product


class Category:
    """Categories table for organizing products"""

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
    def create(self, category_name, description=None, is_active=True, display_order=0, created_by=None):
        sql = """
            INSERT INTO categories (
                category_name, description, is_active, display_order, created_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING category_id;
        """
        now = datetime.utcnow()
        values = (category_name, description, is_active, display_order, created_by, now, now)
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.fetchone()["category_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, category_id):
        sql = "SELECT * FROM categories WHERE category_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (category_id,))
            category = cur.fetchone()
            if category:
                category['products'] = self.get_products(category_id)
            return category

    def get_all(self):
        sql = "SELECT * FROM categories ORDER BY display_order ASC;"
        with self.conn.cursor() as cur:
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
        values.append(datetime.utcnow())
        values.append(category_id)

        sql = f"UPDATE categories SET {', '.join(updates)} WHERE category_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, category_id):
        sql = "DELETE FROM categories WHERE category_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (category_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # RELATED PRODUCTS
    # ---------------------
    def get_products(self, category_id):
        """Fetch products for this category"""
        product_model = Product()
        return product_model.get_by_category(category_id)

    def get_active_products(self, category_id):
        """Get all active products in this category"""
        return [p for p in self.get_products(category_id) if p['is_active']]

    def get_product_count(self, category_id):
        """Total products in this category"""
        return len(self.get_products(category_id))

    def get_active_product_count(self, category_id):
        """Number of active products in this category"""
        return len(self.get_active_products(category_id))
