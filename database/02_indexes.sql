-- ============================================ 
-- INDEXES 
-- ============================================

-- --------------------------------------------
-- Indexes for admin_users
-- --------------------------------------------
CREATE INDEX idx_admin_users_email ON admin_users(email);
CREATE INDEX idx_admin_users_username ON admin_users(username);
CREATE INDEX idx_admin_users_role ON admin_users(role);
CREATE INDEX idx_admin_users_active ON admin_users(is_active);

-- --------------------------------------------
-- Indexes for customers
-- --------------------------------------------
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_username ON customers(username);
CREATE INDEX idx_customers_active ON customers(is_active);

-- --------------------------------------------
-- Indexes for categories
-- --------------------------------------------
CREATE INDEX idx_categories_active ON categories(is_active);
CREATE INDEX idx_categories_display_order ON categories(display_order);
CREATE INDEX idx_categories_name ON categories(category_name);

-- --------------------------------------------
-- Indexes for products
-- --------------------------------------------
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_active ON products(is_active);

-- --------------------------------------------
-- Indexes for shopping_carts
-- --------------------------------------------
CREATE INDEX idx_shopping_carts_customer_id ON shopping_carts(customer_id);
CREATE INDEX idx_shopping_carts_session_id ON shopping_carts(session_id);
CREATE INDEX idx_shopping_carts_expires_at ON shopping_carts(expires_at);

-- --------------------------------------------
-- Indexes for cart_items
-- --------------------------------------------
CREATE INDEX idx_cart_items_shopping_cart_id ON cart_items(shopping_cart_id);
CREATE INDEX idx_cart_items_product_id ON cart_items(product_id);

-- --------------------------------------------
-- Indexes for cart_item_customizations
-- --------------------------------------------
CREATE INDEX idx_cart_item_customizations_cart_item_id 
    ON cart_item_customizations(cart_item_id);
CREATE INDEX idx_cart_item_customizations_key 
    ON cart_item_customizations(customization_key);

-- --------------------------------------------
-- Indexes for orders
-- --------------------------------------------
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_session_id ON orders(session_id);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_order_number ON orders(order_number);

-- --------------------------------------------
-- Indexes for order_items
-- --------------------------------------------
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- --------------------------------------------
-- Indexes for order_item_customizations
-- --------------------------------------------
CREATE INDEX idx_order_item_customizations_order_item_id 
    ON order_item_customizations(order_item_id);
CREATE INDEX idx_order_item_customizations_key 
    ON order_item_customizations(customization_key);

-- --------------------------------------------
-- Indexes for uploaded_files
-- --------------------------------------------
CREATE INDEX idx_uploaded_files_customer_id ON uploaded_files(customer_id);
CREATE INDEX idx_uploaded_files_session_id ON uploaded_files(session_id);
CREATE INDEX idx_uploaded_files_order_item_id ON uploaded_files(order_item_id);
CREATE INDEX idx_uploaded_files_cart_item_id ON uploaded_files(cart_item_id);

-- --------------------------------------------
-- Indexes for order_status_history
-- --------------------------------------------
CREATE INDEX idx_order_status_history_order_id ON order_status_history(order_id);

-- --------------------------------------------
-- Indexes for admin_activity_log
-- --------------------------------------------
CREATE INDEX idx_admin_activity_log_admin_id ON admin_activity_log(admin_id);
CREATE INDEX idx_admin_activity_log_action ON admin_activity_log(action);
CREATE INDEX idx_admin_activity_log_created_at ON admin_activity_log(created_at);

COMMIT;
