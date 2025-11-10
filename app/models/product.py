"""
Product Model  
Represents products available for custom printing
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class Product:
    """Products table"""

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
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (
                category_id, product_name, description, base_price,
                is_active, created_by, updated_by, now, now
            ))
            self.conn.commit()
            return cur.fetchone()["product_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, product_id):
        sql = "SELECT * FROM products WHERE product_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()

    def get_all(self, active_only=True):
        sql = "SELECT * FROM products"
        if active_only:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY product_name ASC;"
        with self.conn.cursor() as cur:
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

        values.append(datetime.utcnow())  # updated_at
        values.append(product_id)  # WHERE condition

        sql = f"""
            UPDATE products
            SET {', '.join(updates)}, updated_at = %s
            WHERE product_id = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, product_id):
        sql = "DELETE FROM products WHERE product_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def get_total_orders(self, product_id):
        """Return total number of order items for this product"""
        sql = "SELECT COUNT(*) FROM order_items WHERE product_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()["count"]

    def get_total_quantity_sold(self, product_id):
        """Return total quantity sold"""
        sql = "SELECT COALESCE(SUM(quantity),0) AS total FROM order_items WHERE product_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            return cur.fetchone()["total"]

    def get_total_revenue(self, product_id):
        """Return total revenue generated"""
        sql = "SELECT COALESCE(SUM(subtotal),0) AS revenue FROM order_items WHERE product_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            return float(cur.fetchone()["revenue"])
        
    def get_by_category(self, category_id):
        """Return all products in a category"""
        sql = "SELECT * FROM products WHERE category_id = %s ORDER BY product_name ASC;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (category_id,))
            return cur.fetchall()
