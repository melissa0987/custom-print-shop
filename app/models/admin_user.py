"""
Admin User Model
Represents administrative users with role-based access control
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AdminUser(Base):
    """Admin users table for staff, admin, and super_admin roles"""
    
    __tablename__ = 'admin_users'
    
    # Primary key
    admin_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Authentication fields
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Role and status
    role = Column(
        String(20), 
        nullable=False,
        server_default='staff'
    )
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_login = Column(TIMESTAMP, nullable=True)
    
    # Foreign key - who created this admin
    created_by = Column(BigInteger, ForeignKey('admin_users.admin_id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    creator = relationship('AdminUser', remote_side=[admin_id], foreign_keys=[created_by], backref='created_admins')
    
    # Products created by this admin
    created_products = relationship('Product', foreign_keys='Product.created_by', back_populates='product_creator')
    updated_products = relationship('Product', foreign_keys='Product.updated_by', back_populates='product_updater')
    
    # Categories created by this admin
    created_categories = relationship('Category', foreign_keys='Category.created_by', back_populates='category_creator')
    updated_categories = relationship('Category', foreign_keys='Category.updated_by', back_populates='category_updater')
    
    # Orders updated by this admin
    updated_orders = relationship('Order', back_populates='updater')
    
    # Order status history
    order_status_changes = relationship('OrderStatusHistory', back_populates='admin')
    
    # Activity logs
    activity_logs = relationship('AdminActivityLog', back_populates='admin')
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "username ~* '^[a-z0-9_-]{3,50}$'",
            name='chk_admin_username_format'
        ),
        CheckConstraint(
            "role IN ('super_admin', 'admin', 'staff')",
            name='chk_admin_role'
        ),
    )
    
    def __repr__(self):
        return f"<AdminUser(admin_id={self.admin_id}, username='{self.username}', role='{self.role}')>"
    
    @property
    def full_name(self):
        """Get admin's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, action):
        """
        Check if admin has permission for an action
        
        Args:
            action (str): Action name to check
            
        Returns:
            bool: True if admin has permission
        """
        if not self.is_active:
            return False
        
        # Super admin can do anything
        if self.role == 'super_admin':
            return True
        
        # Admin permissions
        if self.role == 'admin':
            admin_permissions = [
                'view_orders', 'update_order_status', 'view_customers',
                'view_products', 'add_product', 'update_product',
                'view_categories', 'add_category', 'update_category',
                'view_staff', 'view_reports'
            ]
            return action in admin_permissions
        
        # Staff permissions (read-only + order management)
        if self.role == 'staff':
            staff_permissions = [
                'view_orders', 'update_order_status',
                'view_customers', 'view_products', 'view_categories'
            ]
            return action in staff_permissions
        
        return False