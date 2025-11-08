"""
Order Item Customization Model
Represents customizations for order items
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class OrderItemCustomization(Base):
    """Order item customizations table"""
    
    __tablename__ = 'order_item_customizations'
    
    # Primary key
    customization_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key
    order_item_id = Column(BigInteger, ForeignKey('order_items.order_item_id', ondelete='CASCADE'), nullable=False)
    
    # Customization details
    customization_key = Column(String(100), nullable=False)
    customization_value = Column(Text, nullable=False)
    
    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    order_item = relationship('OrderItem', back_populates='customizations')
    
    def __repr__(self):
        return f"<OrderItemCustomization(customization_id={self.customization_id}, key='{self.customization_key}', value='{self.customization_value}')>"