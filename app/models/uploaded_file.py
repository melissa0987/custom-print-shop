"""
Uploaded File Model  
Represents files uploaded by customers for custom designs
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import current_app


class UploadedFile:
    """Uploaded files table"""

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
    def create(self, file_url, original_filename, customer_id=None, session_id=None,
               order_item_id=None, cart_item_id=None):
        if (customer_id is None and session_id is None) or (customer_id and session_id):
            raise ValueError("UploadedFile must have either customer_id or session_id, not both.")

        uploaded_at = datetime.utcnow()
        sql = """
            INSERT INTO uploaded_files 
            (file_url, original_filename, customer_id, session_id, order_item_id, cart_item_id, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING file_id;
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (file_url, original_filename, customer_id, session_id,
                              order_item_id, cart_item_id, uploaded_at))
            self.conn.commit()
            return cur.fetchone()["file_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, file_id):
        sql = "SELECT * FROM uploaded_files WHERE file_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (file_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM uploaded_files WHERE customer_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()

    def get_by_session(self, session_id):
        sql = "SELECT * FROM uploaded_files WHERE session_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (session_id,))
            return cur.fetchall()
    
    def get_by_cart_item(self, cart_item_id):
        sql = "SELECT * FROM uploaded_files WHERE cart_item_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (cart_item_id,))
            return cur.fetchall()

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, file_id):
        sql = "DELETE FROM uploaded_files WHERE file_id = %s;"
        with self.conn.cursor() as cur:
            cur.execute(sql, (file_id,))
            self.conn.commit()
            return cur.rowcount > 0

    # ---------------------
    # HELPERS
    # ---------------------
    @staticmethod
    def get_file_extension(original_filename):
        return original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''

    @staticmethod
    def is_image(original_filename):
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
        return UploadedFile.get_file_extension(original_filename) in image_extensions

    @staticmethod
    def is_pdf(original_filename):
        return UploadedFile.get_file_extension(original_filename) == 'pdf'
    
 
