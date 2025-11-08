"""
Admin Activity Log Model
Tracks all administrative actions for audit purposes
"""
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, INET
from app.database import Base


class AdminActivityLog(Base):
    """Admin activity log table"""
    
    __tablename__ = 'admin_activity_log'
    
    # Primary key
    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key
    admin_id = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='CASCADE'), nullable=False)
    
    # Activity details
    action = Column(String(50), nullable=False)
    table_name = Column(String(50), nullable=True)
    record_id = Column(BigInteger, nullable=True)
    
    # Change tracking
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    # Request metadata
    ip_address = Column(INET, nullable=True)
    
    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Relationships
    admin = relationship('AdminUser', back_populates='activity_logs')
    
    def __repr__(self):
        return f"<AdminActivityLog(log_id={self.log_id}, admin_id={self.admin_id}, action='{self.action}')>"
    
    def get_admin_name(self):
        """Get name of admin who performed the action"""
        return self.admin.full_name if self.admin else "Unknown"
    
    def get_changes_summary(self):
        """Get a human-readable summary of changes"""
        if not self.old_values and not self.new_values:
            return "No changes recorded"
        
        changes = []
        if self.new_values:
            for key, new_val in self.new_values.items():
                old_val = self.old_values.get(key) if self.old_values else None
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} → {new_val}")
        
        return ", ".join(changes) if changes else "No changes"