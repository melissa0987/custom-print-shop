"""
app/services/cart_service.py
Cart Service
Business logic for shopping cart management

"""

 
from app.models import (
    ShoppingCart, CartItem, CartItemCustomization,
    Product
)
from app.utils import (
    DateHelper,
    FileHelper,
    PriceHelper,
    StringHelper,
    SessionHelper,
    generate_unique_filename,
    format_currency
)


class CartService: 
    
    # Get or create shopping cart
        
    @staticmethod
    def get_or_create_cart(customer_id=None, session_id=None): 
        if not customer_id and not session_id:
            return None
        
        try:
            cart_model = ShoppingCart()
            now = DateHelper.now()

            # Find existing cart
            if customer_id:
                carts = cart_model.get_by_customer(customer_id)
                # Find non-expired cart
                for cart in carts:
                    if cart.get('expires_at') and cart['expires_at'] > now:
                        return cart
            else:
                carts = cart_model.get_by_session(session_id)
                # Find non-expired cart
                for cart in carts:
                    if cart.get('expires_at') and cart['expires_at'] > now:
                        return cart

            # Create new cart if not found
            expires_at = DateHelper.now_plus_days(30)
            cart_id = cart_model.create(
                customer_id=customer_id,
                session_id=session_id or SessionHelper.generate_session_id(),
                expires_at=expires_at
            )
            
            return cart_model.get_by_id(cart_id)

        except Exception as e:
            print(f"Error getting/creating cart: {StringHelper.truncate_text(str(e), 120)}")
            return None
     
    # Add item to cart
    @staticmethod
    def add_to_cart(customer_id, session_id, product_id, quantity, design_file_url=None, customizations=None): 

        if quantity < 1:
            return False, "Quantity must be at least 1"
        
        try:
            product_model = Product()
            product = product_model.get_by_id(product_id)
            
            if not product or not product.get('is_active'):
                return False, "Product not found or inactive"

            # Get or create cart
            cart = CartService.get_or_create_cart(customer_id, session_id)
            if not cart:
                return False, "Failed to create cart"

            cart_item_model = CartItem()
            
            # Check if product already in cart
            cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
            existing_item = None
            for item in cart_items:
                if item['product_id'] == product_id:
                    existing_item = item
                    break

            now = DateHelper.now()

            if existing_item:
                # Update quantity
                new_quantity = existing_item['quantity'] + quantity
                cart_item_model.update(existing_item['cart_item_id'], quantity=new_quantity)
                cart_item_id = existing_item['cart_item_id']
            else:
                # Create new cart item
                if not design_file_url:
                    design_file_url = None
                else:
                    design_file_url = FileHelper.sanitize_url(design_file_url)

                cart_item_id = cart_item_model.create(
                    shopping_cart_id=cart['shopping_cart_id'],
                    product_id=product_id,
                    quantity=quantity,
                    design_file_url=design_file_url
                )

            # Handle customizations
            if customizations:
                customization_model = CartItemCustomization()
                
                # Delete existing customizations for this cart item
                existing_customizations = customization_model.get_by_cart_item(cart_item_id)
                for cust in existing_customizations:
                    customization_model.delete(cust['customization_id'])

                # Add new customizations
                for key, value in customizations.items():
                    customization_model.create(
                        cart_item_id=cart_item_id,
                        customization_key=StringHelper.clean(key),
                        customization_value=StringHelper.clean(str(value))
                    )

             
            cart_model = ShoppingCart() 

            # Calculate total
            cart = cart_model.get_by_id(cart['shopping_cart_id'])
            total = cart_model.calculate_total(cart['shopping_cart_id'])
            formatted_total = format_currency(total)

            return True, {"cart": cart, "formatted_total": formatted_total}

        except Exception as e:
            return False, f"Failed to add to cart: {StringHelper.truncate_text(str(e), 120)}"
     

    #  Update cart item
    @staticmethod
    def update_cart_item(cart_item_id, quantity=None, design_file_url=None,
                         customizations=None, customer_id=None, session_id=None): 
        if quantity is not None and quantity < 1:
            return False, "Quantity must be at least 1"
        
        try:
            cart_item_model = CartItem()
            cart_item = cart_item_model.get_by_id(cart_item_id)

            if not cart_item:
                return False, "Cart item not found"

            # Get cart for ownership check
            cart_model = ShoppingCart()
            cart = cart_model.get_by_id(cart_item['shopping_cart_id'])

            # Ownership check
            has_access = False
            if customer_id and cart.get('customer_id') == customer_id:
                has_access = True
            elif session_id and cart.get('session_id') == session_id:
                has_access = True
            
            if not has_access:
                return False, "Access denied"

            # Update values
            update_kwargs = {}
            if quantity is not None:
                update_kwargs['quantity'] = quantity
            if design_file_url is not None:
                update_kwargs['design_file_url'] = FileHelper.sanitize_url(design_file_url)

            if update_kwargs:
                cart_item_model.update(cart_item_id, **update_kwargs)

            # Handle customizations
            if customizations is not None:
                customization_model = CartItemCustomization()
                
                # Delete existing
                existing = customization_model.get_by_cart_item(cart_item_id)
                for cust in existing:
                    customization_model.delete(cust['customization_id'])
                
                # Add new
                for key, value in customizations.items():
                    customization_model.create(
                        cart_item_id=cart_item_id,
                        customization_key=StringHelper.clean(key),
                        customization_value=StringHelper.clean(str(value))
                    )

            return True, "Cart item updated"

        except Exception as e:
            return False, f"Failed to update cart item: {StringHelper.truncate_text(str(e), 120)}"
    

    # Remove item from cart
    @staticmethod
    def remove_from_cart(cart_item_id, customer_id=None, session_id=None): 
        try:
            cart_item_model = CartItem()
            cart_item = cart_item_model.get_by_id(cart_item_id)
            
            if not cart_item:
                return False, "Cart item not found"

            # Get cart for ownership check
            cart_model = ShoppingCart()
            cart = cart_model.get_by_id(cart_item['shopping_cart_id'])

            # Ownership check
            has_access = False
            if customer_id and cart.get('customer_id') == customer_id:
                has_access = True
            elif session_id and cart.get('session_id') == session_id:
                has_access = True
            
            if not has_access:
                return False, "Access denied"

            cart_item_model.delete(cart_item_id)
            return True, "Item removed from cart"

        except Exception as e:
            return False, f"Failed to remove item: {StringHelper.truncate_text(str(e), 120)}"


    # Clear all items from cart
    @staticmethod
    def clear_cart(customer_id=None, session_id=None): 
        try:
            cart_model = ShoppingCart()
            
            if customer_id:
                carts = cart_model.get_by_customer(customer_id)
            else:
                carts = cart_model.get_by_session(session_id)

            if not carts:
                return True, "Cart already empty"

            # Get the active cart
            cart = carts[0] if carts else None
            if not cart:
                return True, "Cart already empty"

            # Delete all cart items
            cart_item_model = CartItem()
            cart_items = cart_item_model.get_by_cart(cart['shopping_cart_id'])
            for item in cart_items:
                cart_item_model.delete(item['cart_item_id'])

            return True, "Cart cleared"

        except Exception as e:
            return False, f"Failed to clear cart: {StringHelper.truncate_text(str(e), 120)}"


    #  Merge guest cart into customer cart
    @staticmethod
    def merge_guest_cart_to_customer(guest_session_id, customer_id): 
        try:
            cart_model = ShoppingCart()
            cart_item_model = CartItem()
            now = DateHelper.now()

            # Get guest cart
            guest_carts = cart_model.get_by_session(guest_session_id)
            guest_cart = None
            for cart in guest_carts:
                if cart.get('expires_at') and cart['expires_at'] > now:
                    guest_cart = cart
                    break

            if not guest_cart:
                return True, "No guest cart to merge"
            
            guest_cart_items = cart_item_model.get_by_cart(guest_cart['shopping_cart_id'])
            if not guest_cart_items:
                return True, "No guest cart items to merge"

            # Get or create customer cart
            customer_cart = CartService.get_or_create_cart(customer_id, None)
            if not customer_cart:
                return False, "Failed to create customer cart"

            # Merge items
            customer_cart_items = cart_item_model.get_by_cart(customer_cart['shopping_cart_id'])
            
            for guest_item in guest_cart_items:
                # Check if product already in customer cart
                existing_item = None
                for customer_item in customer_cart_items:
                    if customer_item['product_id'] == guest_item['product_id']:
                        existing_item = customer_item
                        break

                if existing_item:
                    # Add quantities
                    new_quantity = existing_item['quantity'] + guest_item['quantity']
                    cart_item_model.update(existing_item['cart_item_id'], quantity=new_quantity)
                else:
                    # Create new item in customer cart
                    cart_item_model.create(
                        shopping_cart_id=customer_cart['shopping_cart_id'],
                        product_id=guest_item['product_id'],
                        quantity=guest_item['quantity'],
                        design_file_url=guest_item.get('design_file_url')
                    )

            # Delete guest cart
            cart_model.delete(guest_cart['shopping_cart_id'])

            return True, "Cart merged successfully"

        except Exception as e:
            return False, f"Failed to merge cart: {StringHelper.truncate_text(str(e), 120)}"


    # Calculate cart total
    @staticmethod
    def calculate_cart_total(shopping_cart_id): 
        try:
            cart_model = ShoppingCart()
            return cart_model.calculate_total(shopping_cart_id)
        except Exception:
            return 0.0
    

    # Get cart item counts
    @staticmethod
    def get_cart_count(customer_id=None, session_id=None): 
        try:
            cart = CartService.get_or_create_cart(customer_id, session_id)
            if not cart:
                return {'total_items': 0, 'total_quantity': 0}
            
            cart_model = ShoppingCart()
            return {
                'total_items': cart_model.get_total_items(cart['shopping_cart_id']),
                'total_quantity': cart_model.get_total_quantity(cart['shopping_cart_id'])
            }
        except Exception:
            return {'total_items': 0, 'total_quantity': 0}
    

    # Remove expired carts (should be run periodically)
    @staticmethod
    def cleanup_expired_carts(): 
        """Remove expired carts (should be run periodically as a background job)"""
        try:
            cart_model = ShoppingCart()
            deleted_count = cart_model.delete_expired_carts()
            
            print(f"Cleaned up {deleted_count} expired carts")
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up carts: {StringHelper.truncate_text(str(e), 120)}")
            return 0