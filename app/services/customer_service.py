"""
app/services/customer_service.py
Customer Service
Business logic for Customer operations

"""

from app.models.customer import Customer
from app.utils import Validators, StringHelper, PriceHelper 
from werkzeug.security import check_password_hash, generate_password_hash

class CustomerService:

    @staticmethod
    def get_customer(customer_id):
        model = Customer()
        customer = model.get_by_id(customer_id)
        return customer

    @staticmethod
    def update_profile(customer_id, **kwargs):
        model = Customer()
        
        # Remove None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            return False, "No changes to update"
        
        # Validate email if provided
        if 'email' in update_data and not Validators.validate_email(update_data['email']):
            return False, "Invalid email address"
        
        # Validate username if provided
        if 'username' in update_data and not Validators.validate_username(update_data['username']):
            return False, "Invalid username format"
        
        if 'address' in update_data and len(update_data['address']) > 255:
            return False, "Address is too long"
        
        updated = model.update(customer_id, **update_data)
        if not updated:
            return False, "Failed to update profile"
        
        customer = model.get_by_id(customer_id)
        return True, customer

    @staticmethod
    def change_password(customer_id, current_password, new_password):
        """Change customer password"""
        
        try:
            model = Customer()
            customer = model.get_by_id(customer_id)
            
            if not customer:
                return False, "Customer not found"
            
            # Verify current password
            if not check_password_hash(customer['password_hash'], current_password):
                return False, "Current password is incorrect"
            
            # Don't allow same password
            if check_password_hash(customer['password_hash'], new_password):
                return False, "New password must be different from current password"
            
            # Update password
            new_hash = generate_password_hash(new_password)
            updated = model.update(customer_id, password_hash=new_hash)
            
            if not updated:
                return False, "Failed to update password"
            
            return True, "Password updated successfully"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def change_password_as_admin(customer_id, new_password):
        """Change customer password"""
        
        try:
            model = Customer()
            customer = model.get_by_id(customer_id)
            
            if not customer:
                return False, "Customer not found"

            # Update password
            new_hash = generate_password_hash(new_password)
            updated = model.update(customer_id, password_hash=new_hash)
            
            if not updated:
                return False, "Failed to update password"
            
            return True, "Password updated successfully"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
