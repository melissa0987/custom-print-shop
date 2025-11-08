"""
Cart Item Model
Represents individual items in shopping carts
"""
from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CartItem(Base):
    """Cart items table"""
    
    __tablename__ = 'cart_items'
    
    # Primary key
    cart_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign keys
    shopping_cart_id = Column(BigInteger, ForeignKey('shopping_carts.shopping_cart_id', ondelete='CASCADE'), nullable=False)
    product_id = Column(BigInteger, ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    
    # Item details
    quantity = Column(Integer, nullable=False)
    design_file_url = Column(Text, nullable=True)
    
    # Timestamps
    added_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    shopping_cart = relationship('ShoppingCart', back_populates='cart_items')
    product = relationship('Product', back_populates='cart_items')
    customizations = relationship('CartItemCustomization', back_populates='cart_item', cascade='all, delete-orphan')
    uploaded_files = relationship('UploadedFile', back_populates='cart_item')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_cart_item_quantity'),
    )
    
    def __repr__(self):
        return f"<CartItem(cart_item_id={self.cart_item_id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    def get_line_total(self):
        """Calculate line total (quantity * product price)"""
        return float(self.quantity * self.product.base_price)
    
    def get_customizations_dict(self):
        """Get customizations as dictionary"""
        return {c.customization_key: c.customization_value for c in self.customizations}
    
    def add_customization(self, key, value):
        """Add a customization to this cart item"""
        from app.models.cart_item_customization import CartItemCustomization
        customization = CartItemCustomization(
            cart_item_id=self.cart_item_id,
            customization_key=key,
            customization_value=value
        )
        self.customizations.append(customization)
        return customization