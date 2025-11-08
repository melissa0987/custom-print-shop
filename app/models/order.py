"""
Order Model
Represents customer orders
"""
from sqlalchemy import Column, BigInteger, String, Text, NUMERIC, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    """Orders table"""
    
    __tablename__ = 'orders'
    
    # Primary key
    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Owner (either customer or guest session)
    customer_id = Column(BigInteger, ForeignKey('customers.customer_id', ondelete='SET NULL'), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Order information
    order_number = Column(String(50), unique=True, nullable=False)
    order_status = Column(String(20), nullable=False, default='pending')
    total_amount = Column(NUMERIC(10, 2), nullable=False)
    
    # Shipping and contact information
    shipping_address = Column(Text, nullable=False)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Foreign key - who last updated this order
    updated_by = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    customer = relationship('Customer', back_populates='orders')
    updater = relationship('AdminUser', back_populates='updated_orders')
    order_items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    status_history = relationship('OrderStatusHistory', back_populates='order', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "order_status IN ('pending', 'processing', 'completed', 'cancelled')",
            name='chk_order_status'
        ),
        CheckConstraint('total_amount >= 0', name='chk_order_total_amount'),
    )
    
    def __repr__(self):
        return f"<Order(order_id={self.order_id}, order_number='{self.order_number}', status='{self.order_status}')>"
    
    def get_total_items(self):
        """Get total number of items in order"""
        return len(self.order_items)
    
    def get_total_quantity(self):
        """Get total quantity of all items in order"""
        return sum(item.quantity for item in self.order_items)
    
    def calculate_total(self):
        """Calculate total from order items"""
        return float(sum(item.subtotal for item in self.order_items))
    
    def get_customer_name(self):
        """Get customer name or 'Guest' for guest orders"""
        if self.customer:
            return self.customer.full_name
        return "Guest"
    
    def get_customer_email(self):
        """Get customer email"""
        return self.customer.email if self.customer else self.contact_email
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.order_status in ['pending', 'processing']
    
    def can_be_updated(self):
        """Check if order can be updated"""
        return self.order_status != 'completed'