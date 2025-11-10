"""
Order Status History Model  
Tracks all status changes for orders
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class OrderStatusHistory:
    """Order status history table"""

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
    def create(self, order_id, status, changed_by=None, notes=None):
        """Insert a new status change"""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        sql = """
            INSERT INTO order_status_history (
                order_id, status, changed_by, notes, changed_at
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING history_id;
        """
        now = datetime.utcnow()
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id, status, changed_by, notes, now))
            self.conn.commit()
            return cur.fetchone()["history_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, history_id):
        sql = "SELECT * FROM order_status_history WHERE history_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (history_id,))
            return cur.fetchone()

    def get_by_order(self, order_id):
        sql = "SELECT * FROM order_status_history WHERE order_id = %s ORDER BY changed_at ASC;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (order_id,))
            return cur.fetchall()

    # ---------------------
    # UPDATE
    # ---------------------
    def update(self, history_id, status=None, notes=None, changed_by=None):
        updates = []
        values = []

        if status is not None:
            if status not in self.VALID_STATUSES:
                raise ValueError(f"Invalid status: {status}")
            updates.append("status = %s")
            values.append(status)
        if notes is not None:
            updates.append("notes = %s")
            values.append(notes)
        if changed_by is not None:
            updates.append("changed_by = %s")
            values.append(changed_by)
        if not updates:
            return False

        sql = f"UPDATE order_status_history SET {', '.join(updates)} WHERE history_id = %s;"
        values.append(history_id)

        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, history_id):
        sql = "DELETE FROM order_status_history WHERE history_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (history_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    def get_changed_by_name(self, history_record):
        """Return admin name or 'System' if None"""
        if history_record.get("changed_by"):
            from .admin_user import AdminUser
            admin_model = AdminUser()
            admin = admin_model.get_by_id(history_record["changed_by"])
            if admin:
                return f"{admin['first_name']} {admin['last_name']}"
        return "System"
