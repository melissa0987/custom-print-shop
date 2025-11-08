"""
Category Model
Represents product categories
"""
from sqlalchemy import Column, BigInteger, String, Boolean, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Category(Base):
    """Categories table for organizing products"""
    
    __tablename__ = 'categories'
    
    # Primary key
    category_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Category information
    category_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Status and ordering
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Foreign keys - tracking who created/updated
    created_by = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='SET NULL'), nullable=True)
    updated_by = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    category_creator = relationship('AdminUser', foreign_keys=[created_by], back_populates='created_categories')
    category_updater = relationship('AdminUser', foreign_keys=[updated_by], back_populates='updated_categories')
    products = relationship('Product', back_populates='category')
    
    def __repr__(self):
        return f"<Category(category_id={self.category_id}, name='{self.category_name}')>"
    
    def get_active_products(self):
        """Get all active products in this category"""
        return [product for product in self.products if product.is_active]
    
    def get_product_count(self):
        """Get total number of products in this category"""
        return len(self.products)
    
    def get_active_product_count(self):
        """Get number of active products in this category"""
        return len(self.get_active_products())