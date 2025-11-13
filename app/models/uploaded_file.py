"""
app/models/uploaded_file.py
Uploaded File Model  
Represents files uploaded by customers for custom designs
"""
from app.database import get_cursor
from datetime import datetime
 
class UploadedFile: 
    def __init__( self, file_id=None, customer_id=None, session_id=None, order_item_id=None, cart_item_id=None, file_url=None, original_filename=None, uploaded_at=None ):
        

        self.file_id = file_id
        self.customer_id = customer_id
        self.session_id = session_id
        self.order_item_id = order_item_id
        self.cart_item_id = cart_item_id
        self.file_url = file_url
        self.original_filename = original_filename
        self.uploaded_at = uploaded_at or datetime.now()

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'customer_id': self.customer_id,
            'session_id': self.session_id,
            'order_item_id': self.order_item_id,
            'cart_item_id': self.cart_item_id,
            'file_url': self.file_url,
            'original_filename': self.original_filename,
            'uploaded_at': self.uploaded_at.isoformat()
        }
    # ---------------------
    # CREATE
    # ---------------------
    def create(self, file_url, original_filename, customer_id=None, session_id=None,
               order_item_id=None, cart_item_id=None):
        if (customer_id is None and session_id is None) or (customer_id and session_id):
            raise ValueError("UploadedFile must have either customer_id or session_id, not both.")

        uploaded_at = datetime.now()
        sql = """
            INSERT INTO uploaded_files 
            (file_url, original_filename, customer_id, session_id, order_item_id, cart_item_id, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING file_id;
        """
        with get_cursor() as cur:
            cur.execute(sql, (file_url, original_filename, customer_id, session_id,
                              order_item_id, cart_item_id, uploaded_at))
            
            return cur.fetchone()["file_id"]
        
    def update_session_to_customer(self, session_id, customer_id):
        """Update uploaded files from session to customer after registration"""
        sql = """
            UPDATE uploaded_files 
            SET customer_id = %s, session_id = NULL 
            WHERE session_id = %s;
        """
        with get_cursor() as cur:
            cur.execute(sql, (customer_id, session_id))
            return cur.rowcount > 0

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, file_id):
        sql = "SELECT * FROM uploaded_files WHERE file_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (file_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM uploaded_files WHERE customer_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()

    def get_by_session(self, session_id):
        sql = "SELECT * FROM uploaded_files WHERE session_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (session_id,))
            return cur.fetchall()
    
    def get_by_cart_item(self, cart_item_id):
        sql = "SELECT * FROM uploaded_files WHERE cart_item_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cart_item_id,))
            return cur.fetchall()

    def get_orphaned_files(self, cutoff_date):
        """Get files not attached to any cart or order, older than cutoff_date"""
        sql = """
            SELECT * FROM uploaded_files 
            WHERE cart_item_id IS NULL 
            AND order_item_id IS NULL 
            AND uploaded_at < %s
            ORDER BY uploaded_at ASC;
        """
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (cutoff_date,))
            return cur.fetchall()
        

    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, file_id):
        sql = "DELETE FROM uploaded_files WHERE file_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (file_id,))
            
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
    
 
