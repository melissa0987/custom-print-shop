"""
Customer Model
Represents customers who can place orders
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Customer(Base):
    """Customers table"""
    
    __tablename__ = 'customers'
    
    # Primary key
    customer_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Authentication fields
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_login = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    shopping_carts = relationship('ShoppingCart', back_populates='customer', cascade='all, delete-orphan')
    orders = relationship('Order', back_populates='customer')
    uploaded_files = relationship('UploadedFile', back_populates='customer', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "username ~* '^[a-z0-9_-]{3,50}$'",
            name='chk_username_format'
        ),
    )
    
    def __repr__(self):
        return f"<Customer(customer_id={self.customer_id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self):
        """Get customer's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_active_cart(self):
        """Get customer's active shopping cart"""
        from datetime import datetime
        for cart in self.shopping_carts:
            if cart.expires_at and cart.expires_at > datetime.now():
                return cart
        return None
    
    def get_order_history(self):
        """Get customer's order history, sorted by date"""
        return sorted(self.orders, key=lambda x: x.created_at, reverse=True)
    
    def get_total_spent(self):
        """Calculate total amount spent by customer on completed orders"""
        from sqlalchemy import func as sql_func
        from app.models.order import Order
        
        total = sum(
            order.total_amount 
            for order in self.orders 
            if order.order_status == 'completed'
        )
        return total or 0
    
    def get_order_count(self):
        """Get total number of orders placed by customer"""
        return len(self.orders)