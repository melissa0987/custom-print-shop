"""
Order Item Model
Represents individual items in orders
"""
from sqlalchemy import Column, BigInteger, Integer, Text, NUMERIC, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class OrderItem(Base):
    """Order items table"""
    
    __tablename__ = 'order_items'
    
    # Primary key
    order_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign keys
    order_id = Column(BigInteger, ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False)
    product_id = Column(BigInteger, ForeignKey('products.product_id', ondelete='RESTRICT'), nullable=False)
    
    # Item details
    quantity = Column(Integer, nullable=False)
    unit_price = Column(NUMERIC(10, 2), nullable=False)
    design_file_url = Column(Text, nullable=True)
    subtotal = Column(NUMERIC(10, 2), nullable=False)
    
    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    order = relationship('Order', back_populates='order_items')
    product = relationship('Product', back_populates='order_items')
    customizations = relationship('OrderItemCustomization', back_populates='order_item', cascade='all, delete-orphan')
    uploaded_files = relationship('UploadedFile', back_populates='order_item')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_order_item_quantity'),
        CheckConstraint('unit_price >= 0', name='chk_order_item_unit_price'),
        CheckConstraint('subtotal >= 0', name='chk_order_item_subtotal'),
    )
    
    def __repr__(self):
        return f"<OrderItem(order_item_id={self.order_item_id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    def get_customizations_dict(self):
        """Get customizations as dictionary"""
        return {c.customization_key: c.customization_value for c in self.customizations}
    
    def calculate_subtotal(self):
        """Calculate subtotal (quantity * unit_price)"""
        return float(self.quantity * self.unit_price)