"""
Cart Item Customization Model
Represents customizations for cart items (e.g., size, color, print location)
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CartItemCustomization(Base):
    """Cart item customizations table"""
    
    __tablename__ = 'cart_item_customizations'
    
    # Primary key
    customization_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key
    cart_item_id = Column(BigInteger, ForeignKey('cart_items.cart_item_id', ondelete='CASCADE'), nullable=False)
    
    # Customization details
    customization_key = Column(String(100), nullable=False)
    customization_value = Column(Text, nullable=False)
    
    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    cart_item = relationship('CartItem', back_populates='customizations')
    
    def __repr__(self):
        return f"<CartItemCustomization(customization_id={self.customization_id}, key='{self.customization_key}', value='{self.customization_value}')>"