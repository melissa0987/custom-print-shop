"""
Order Model  
Represents customer orders
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class Order:
    """Orders table"""

    VALID_STATUSES = ('pending', 'processing', 'completed', 'cancelled')

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
    def create(self, order_number, total_amount, shipping_address, 
               customer_id=None, session_id=None, order_status='pending',
               contact_phone=None, contact_email=None, notes=None, updated_by=None):
        if order_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {order_status}")

        sql = """
            INSERT INTO orders (
                customer_id, session_id, order_number, order_status,
                total_amount, shipping_address, contact_phone,
                contact_email, notes, updated_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id;
        """
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (
                customer_id, session_id, order_number, order_status,
                total_amount, shipping_address, contact_phone,
                contact_email, notes, updated_by, now, now
            ))
            self.conn.commit()
            return cur.fetchone()["order_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, order_id):
        sql = "SELECT * FROM orders WHERE order_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM orders WHERE customer_id = %s ORDER BY created_at DESC;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update_status(self, order_id, order_status, updated_by=None):
        if order_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {order_status}")

        sql = """
            UPDATE orders
            SET order_status = %s, updated_at = %s, updated_by = %s
            WHERE order_id = %s;
        """
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_status, now, updated_by, order_id))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, order_id):
        sql = "DELETE FROM orders WHERE order_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def can_be_cancelled(self, order_record):
        """Check if order can be cancelled"""
        return order_record["order_status"] in ['pending', 'processing']

    def can_be_updated(self, order_record):
        """Check if order can be updated"""
        return order_record["order_status"] != 'completed'

    def get_customer_name(self, order_record, customer_model=None):
        """Return customer full name or 'Guest'"""
        if order_record.get("customer_id") and customer_model:
            customer = customer_model.get_by_id(order_record["customer_id"])
            if customer:
                return f"{customer['first_name']} {customer['last_name']}"
        return "Guest"

    def get_customer_email(self, order_record, customer_model=None):
        """Return customer email"""
        if order_record.get("customer_id") and customer_model:
            customer = customer_model.get_by_id(order_record["customer_id"])
            if customer:
                return customer.get("email")
        return order_record.get("contact_email")
