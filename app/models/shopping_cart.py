"""
Shopping Cart Model
Represents shopping carts for customers and guest users
"""
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.database import Base


class ShoppingCart(Base):
    """Shopping carts table"""
    
    __tablename__ = 'shopping_carts'
    
    # Primary key
    shopping_cart_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Owner (either customer or guest session)
    customer_id = Column(BigInteger, ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    expires_at = Column(TIMESTAMP, default=lambda: datetime.now() + timedelta(days=30))
    
    # Relationships
    customer = relationship('Customer', back_populates='shopping_carts')
    cart_items = relationship('CartItem', back_populates='shopping_cart', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NOT NULL AND session_id IS NULL) OR (customer_id IS NULL AND session_id IS NOT NULL)",
            name='chk_cart_owner'
        ),
    )
    
    def __repr__(self):
        owner = f"customer_id={self.customer_id}" if self.customer_id else f"session_id={self.session_id}"
        return f"<ShoppingCart(shopping_cart_id={self.shopping_cart_id}, {owner})>"
    
    def is_expired(self):
        """Check if cart has expired"""
        return self.expires_at and self.expires_at < datetime.now()
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return len(self.cart_items)
    
    def get_total_quantity(self):
        """Get total quantity of all items in cart"""
        return sum(item.quantity for item in self.cart_items)
    
    def calculate_total(self):
        """Calculate total price of all items in cart"""
        total = sum(item.quantity * item.product.base_price for item in self.cart_items)
        return float(total)
    
    def clear(self):
        """Remove all items from cart"""
        self.cart_items.clear()