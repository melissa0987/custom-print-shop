"""
Uploaded File Model
Represents files uploaded by customers for custom designs
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UploadedFile(Base):
    """Uploaded files table"""
    
    __tablename__ = 'uploaded_files'
    
    # Primary key
    file_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Owner (either customer or guest session)
    customer_id = Column(BigInteger, ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Associated order or cart item
    order_item_id = Column(BigInteger, ForeignKey('order_items.order_item_id', ondelete='SET NULL'), nullable=True)
    cart_item_id = Column(BigInteger, ForeignKey('cart_items.cart_item_id', ondelete='SET NULL'), nullable=True)
    
    # File details
    file_url = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=False)
    
    # Timestamp
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    customer = relationship('Customer', back_populates='uploaded_files')
    order_item = relationship('OrderItem', back_populates='uploaded_files')
    cart_item = relationship('CartItem', back_populates='uploaded_files')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NOT NULL AND session_id IS NULL) OR (customer_id IS NULL AND session_id IS NOT NULL)",
            name='chk_file_owner'
        ),
    )
    
    def __repr__(self):
        return f"<UploadedFile(file_id={self.file_id}, filename='{self.original_filename}')>"
    
    def get_file_extension(self):
        """Get file extension"""
        return self.original_filename.rsplit('.', 1)[-1].lower() if '.' in self.original_filename else ''
    
    def is_image(self):
        """Check if file is an image"""
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
        return self.get_file_extension() in image_extensions
    
    def is_pdf(self):
        """Check if file is a PDF"""
        return self.get_file_extension() == 'pdf'