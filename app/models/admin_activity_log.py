"""
Admin Activity Log Model 
Tracks all administrative actions for audit purposes
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class AdminActivityLog:
    """Handles admin activity log operations using psycopg2"""

    def __init__(self):
        self.conn = psycopg2.connect(
            current_app.config['SQLALCHEMY_DATABASE_URI'].replace(
                "postgresql+psycopg2", "postgresql"
            ),
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def __del__(self):
        """Ensure connection closes"""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass

    def create_log(self, admin_id, action, table_name=None, record_id=None,
                   old_values=None, new_values=None, ip_address=None):
        """
        Insert a new admin activity log record.
        """
        sql = """
            INSERT INTO admin_activity_log (
                admin_id, action, table_name, record_id,
                old_values, new_values, ip_address, created_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            RETURNING log_id;
        """
        values = (
            admin_id,
            action,
            table_name,
            record_id,
            psycopg2.extras.Json(old_values) if old_values else None,
            psycopg2.extras.Json(new_values) if new_values else None,
            ip_address,
            datetime.utcnow()
        )

        with self.conn.cursor() as cur:
            cur.execute(sql, values)
            self.conn.commit()
            return cur.fetchone()["log_id"]

    def get_all_logs(self, limit=50):
        """
        Fetch recent admin activity logs.
        """
        sql = """
            SELECT log_id, admin_id, action, table_name, record_id,
                   old_values, new_values, ip_address, created_at
            FROM admin_activity_log
            ORDER BY created_at DESC
            LIMIT %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def get_log_by_id(self, log_id):
        """
        Fetch a specific log by ID.
        """
        sql = "SELECT * FROM admin_activity_log WHERE log_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (log_id,))
            return cur.fetchone()

    def delete_log(self, log_id):
        """
        Delete a log entry by ID.
        """
        sql = "DELETE FROM admin_activity_log WHERE log_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (log_id,))
            self.conn.commit()
            return cur.rowcount > 0
