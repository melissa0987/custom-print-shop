"""
app/models/order.py
Order Model  
Represents customer orders
"""


from app.database import get_cursor
from datetime import datetime

from app.models.order_item_customization import OrderItemCustomization  
 


class Order:
    """Orders table""" 
    VALID_STATUSES = ['pending', 'processing', 'completed', 'cancelled']
    def __init__( self, order_id=None, customer_id=None, session_id=None, order_number=None, order_status='pending', 
                 total_amount=0.0, shipping_address=None, contact_phone=None,  contact_email=None, notes=None, 
                 created_at=None, updated_at=None, updated_by=None ):
        

        self.order_id = order_id
        self.customer_id = customer_id
        self.session_id = session_id
        self.order_number = order_number
        self.order_status = order_status
        self.total_amount = float(total_amount)
        self.shipping_address = shipping_address
        self.contact_phone = contact_phone
        self.contact_email = contact_email
        self.notes = notes
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.updated_by = updated_by

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'customer_id': self.customer_id,
            'session_id': self.session_id,
            'order_number': self.order_number,
            'order_status': self.order_status,
            'total_amount': self.total_amount,
            'shipping_address': self.shipping_address,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by
        }

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
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute(sql, (
                customer_id, session_id, order_number, order_status,
                total_amount, shipping_address, contact_phone,
                contact_email, notes, updated_by, now, now
            ))
             
            return cur.fetchone()["order_id"]

    # ---------------------
    # READ
    # ---------------------
    def get_by_id(self, order_id):
        sql = "SELECT * FROM orders WHERE order_id = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (order_id,))
            return cur.fetchone()

    def get_by_customer(self, customer_id):
        sql = "SELECT * FROM orders WHERE customer_id = %s ORDER BY created_at DESC;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (customer_id,))
            return cur.fetchall()
        
    def get_all(self, limit=None):
        """Get all orders"""
        sql = "SELECT * FROM orders ORDER BY created_at DESC"
        if limit:
            sql += f" LIMIT {limit};"
        else:
            sql += ";"
        with get_cursor(commit=False) as cur:
            cur.execute(sql)
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
        now = datetime.now()
        with get_cursor() as cur:
            cur.execute(sql, (order_status, now, updated_by, order_id))
            return cur.rowcount > 0

    def update(self, order_id, fields: dict): 
        if not fields:
            return False

        allowed_fields = {
            'order_number', 'order_status', 'total_amount', 'shipping_address',
            'contact_phone', 'contact_email', 'notes', 'updated_by'
        }

        # Filter out invalid keys
        updates = {k: v for k, v in fields.items() if k in allowed_fields}
        if not updates:
            return False

        updates['updated_at'] = datetime.now()

        # Build SET clause dynamically
        set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
        values = list(updates.values()) + [order_id]

        sql = f"UPDATE orders SET {set_clause} WHERE order_id = %s;"

        with get_cursor() as cur:
            cur.execute(sql, values)
            return cur.rowcount > 0
        
        
    # ---------------------
    # DELETE
    # ---------------------
    def delete(self, order_id):
        sql = "DELETE FROM orders WHERE order_id = %s;"
        with get_cursor() as cur:
            cur.execute(sql, (order_id,))
             
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
    
    def get_by_order_number(self, order_number):
        """Get order by order number"""
        sql = "SELECT * FROM orders WHERE order_number = %s;"
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (order_number,))
            return cur.fetchone()
        
    def get_order_with_details(self, order_id):
        """Get order with all related information including items"""
        sql = """
            SELECT 
                o.*,
                c.username, c.email, c.first_name, c.last_name
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_id = %s;
        """
        with get_cursor(commit=False) as cur:
            cur.execute(sql, (order_id,))
            order = cur.fetchone()
            
            if not order:
                return None
            
            # Get order items with product and category details
            items_sql = """
                SELECT 
                    oi.order_item_id,
                    oi.quantity,
                    oi.unit_price,
                    oi.subtotal,
                    oi.design_file_url,
                    p.product_id,
                    p.product_name,
                    cat.category_name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                JOIN categories cat ON p.category_id = cat.category_id
                WHERE oi.order_id = %s;
            """
            cur.execute(items_sql, (order_id,))
            items = cur.fetchall()
            
            # Get customizations for each item
            order_item_customization_model = OrderItemCustomization()
            for item in items:
                customizations = order_item_customization_model.get_by_order_item(
                    item['order_item_id']
                )
                item['customizations'] = {
                    c['customization_key']: c['customization_value'] 
                    for c in customizations
                } if customizations else {}
            
            # Attach items to order
            order['items'] = items
            
            return order