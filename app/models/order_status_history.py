"""
Order Status History Model
Tracks all status changes for orders
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class OrderStatusHistory(Base):
    """Order status history table"""
    
    __tablename__ = 'order_status_history'
    
    # Primary key
    history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign keys
    order_id = Column(BigInteger, ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False)
    changed_by = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='SET NULL'), nullable=True)
    
    # Status change details
    status = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamp
    changed_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    order = relationship('Order', back_populates='status_history')
    admin = relationship('AdminUser', back_populates='order_status_changes')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'cancelled')",
            name='chk_order_status_history_status'
        ),
    )
    
    def __repr__(self):
        return f"<OrderStatusHistory(history_id={self.history_id}, order_id={self.order_id}, status='{self.status}')>"
    
    def get_changed_by_name(self):
        """Get name of admin who changed the status"""
        if self.admin:
            return self.admin.full_name
        return "System"