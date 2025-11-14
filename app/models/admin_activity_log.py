"""
app/models/admin_activity_log.py
Admin Activity Log Model 
Tracks all administrative actions for audit purposes
"""

from flask import json
from app.database import get_cursor
from datetime import datetime
from zoneinfo import ZoneInfo

# Handles admin activity log operations 
class AdminActivityLog:
    

    def __init__(
        self,
        log_id=None,
        admin_id=None,
        action=None,
        table_name=None,
        record_id=None,
        old_values=None,
        new_values=None,
        ip_address=None,
        created_at=None
    ):
        self.log_id = log_id
        self.admin_id = admin_id
        self.action = action
        self.table_name = table_name
        self.record_id = record_id
        self.old_values = old_values
        self.new_values = new_values
        self.ip_address = ip_address
        self.created_at = datetime.now() 

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'admin_id': self.admin_id,
            'action': self.action,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }



    def create_log(self, admin_id, action, table_name=None, record_id=None,
                old_values=None, new_values=None, ip_address=None): 
        
        sql = """
            INSERT INTO admin_activity_log (
                admin_id, action, table_name, record_id,
                old_values, new_values, ip_address, created_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            RETURNING log_id;
        """

        # Convert dicts to JSON strings
        old_json = json.dumps(old_values) if old_values else None
        new_json = json.dumps(new_values) if new_values else None

        values = (
            admin_id,
            action,
            table_name,
            record_id,
            old_json,         
            new_json,         
            ip_address,
            datetime.now()
        )

        with get_cursor() as cur:
            cur.execute(sql, values)
            return cur.fetchone()["log_id"]

    # Fetch recent admin activity logs.
    def get_all_logs(self, limit=50):
        
        sql = """
            SELECT log_id, admin_id, action, table_name, record_id,
                   old_values, new_values, ip_address, created_at
            FROM admin_activity_log
            ORDER BY created_at DESC
            LIMIT %s;
        """
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    # Fetch a specific log by ID.
    def get_log_by_id(self, log_id):
        
        sql = "SELECT * FROM admin_activity_log WHERE log_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (log_id,))
            return cur.fetchone()

    # Delete a log entry by ID.
    def delete_log(self, log_id): 
        sql = "DELETE FROM admin_activity_log WHERE log_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (log_id,))
            
            return cur.rowcount > 0
