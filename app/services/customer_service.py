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
        # Basic validation (optional)
        if 'email' in kwargs and not Validators.validate_email(kwargs['email']):
            return False, "Invalid email address"
        
        updated = model.update(customer_id, **kwargs)
        if not updated:
            return False, "No changes were made"
        
        customer = model.get_by_id(customer_id)
        return True, customer

    @staticmethod
    def change_password(customer_id, current_password, new_password):
        model = Customer()
        customer = model.get_by_id(customer_id)
        if not customer:
            return False, "Customer not found"

        if not check_password_hash(customer['password_hash'], current_password):
            return False, "Current password is incorrect"

        new_hash = generate_password_hash(new_password)
        updated = model.update(customer_id, password_hash=new_hash)
        if not updated:
            return False, "Failed to update password"

        return True, "Password updated successfully"
