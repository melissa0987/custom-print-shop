
-- Insert Sample Admin Users 
INSERT INTO admin_users (username, email, password_hash, first_name, last_name, role, is_active) VALUES
    ('superadmin', 'superadmin@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Super', 'Admin', 'super_admin', TRUE),
    ('admin_john', 'john.admin@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'John', 'Admin', 'super_admin', TRUE),
    ('staff_jane', 'jane.staff@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Jane', 'Administrator', 'admin', TRUE),
    ('admin_emily', 'emily.admin@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Emily', 'Administrator', 'admin', TRUE),
    ('staff_michael', 'michael.staff@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Michael', 'Staff', 'staff', TRUE),
    ('staff_sophia', 'sophia.staff@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Sophia', 'Staff', 'staff', TRUE),
    ('admin_david', 'david.admin@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'David', 'Administrator', 'admin', TRUE),
    ('staff_olivia', 'olivia.staff@printcraft.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Olivia', 'Staff', 'staff', TRUE);

-- Insert Sample Customers
INSERT INTO customers (username, email, password_hash, first_name, last_name, phone_number) VALUES
    ('johndoe', 'john.doe@email.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'John', 'Doe', '514-555-0101'),
    ('janesmith', 'jane.smith@email.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Jane', 'Smith', '514-555-0102'),
    ('bobwilson', 'bob.wilson@email.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Bob', 'Wilson', '514-555-0103'),
    ('alicebrown', 'alice.brown@email.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Alice', 'Brown', '514-555-0104'),
    ('charliedavis', 'charlie.davis@email.com', 'scrypt:32768:8:1$w8mk452lIinHUfCY$7f600ca2108e6e740d9f5c627e521ce2b835b1a0923f877d1a49b8a384d10da11a6a9a9cc6dfc8f12be51d331909260164be0a15e4f986cd8f6fb03945d0cc34', 'Charlie', 'Davis', '514-555-0105');

-- Insert Categories (created by admin_john with admin_id = 2)
INSERT INTO categories (category_name, description, is_active, display_order, created_by, updated_by) VALUES
    ('Mugs', 'Ceramic and insulated mugs for hot and cold beverages', TRUE, 1, 2, 2),
    ('Tumblers', 'Insulated stainless steel tumblers', TRUE, 2, 2, 2),
    ('Bags', 'Tote bags, drawstring bags, and shopping bags', TRUE, 3, 2, 2),
    ('T-Shirts', 'Custom printed t-shirts in various sizes', TRUE, 4, 2, 2);

-- Insert Sample Products (created by admin_john with admin_id = 2)
INSERT INTO products (category_id, product_name, description, base_price, is_active, created_by, updated_by) VALUES
    -- Mugs (category_id = 1)
    (1, 'Ceramic Mug 11oz', 'Classic white ceramic mug, dishwasher safe', 12.99, TRUE, 2, 2),
    (1, 'Ceramic Mug 15oz', 'Large ceramic mug, perfect for coffee lovers', 14.99, TRUE, 2, 2), 
    
    -- Tumblers (category_id = 2)
    (2, 'Stainless Tumbler 20oz', 'Double-wall insulated tumbler', 24.99, TRUE, 2, 2),
    (2, 'Stainless Tumbler 30oz', 'Large insulated tumbler with straw', 29.99, TRUE, 2, 2),
    
    -- Bags (category_id = 3)
    (3, 'Canvas Tote Bag', 'Durable canvas tote bag, 15x16 inches', 16.99, TRUE, 2, 2),
    (3, 'Cotton Drawstring Bag', 'Lightweight cotton drawstring bag', 9.99, TRUE, 2, 2), 
    
    -- T-Shirts (category_id = 4)
    (4, 'Cotton T-Shirt - S', 'Premium 100% cotton t-shirt, size Small', 19.99, TRUE, 2, 2),
    (4, 'Cotton T-Shirt - M', 'Premium 100% cotton t-shirt, size Medium', 19.99, TRUE, 2, 2),
    (4, 'Cotton T-Shirt - L', 'Premium 100% cotton t-shirt, size Large', 19.99, TRUE, 2, 2),
    (4, 'Cotton T-Shirt - XL', 'Premium 100% cotton t-shirt, size XL', 19.99, TRUE, 2, 2);

-- Insert Sample Shopping Carts (customer and guest carts)
INSERT INTO shopping_carts (customer_id, session_id) VALUES
    (1, NULL),  -- johndoe's cart
    (2, NULL),  -- janesmith's cart
    (NULL, 'guest-session-12345'),  -- Guest cart 1
    (NULL, 'guest-session-67890');  -- Guest cart 2

-- Insert Sample Cart Items
INSERT INTO cart_items (shopping_cart_id, product_id, quantity, design_file_url) VALUES
    -- johndoe's cart (shopping_cart_id = 1)
    (1, 1, 2, '../icons/mug.png'),
    (1, 4, 1, '../icons/mug.png'),
    
    -- janesmith's cart (shopping_cart_id = 2)
    (2, 6, 1, NULL),
    (2, 10, 2, '../icons/mug.png'),
    
    -- Guest cart 1 (shopping_cart_id = 3)
    (3, 3, 1, '../icons/mug.png'),
    
    -- Guest cart 2 (shopping_cart_id = 4)
    (4, 6, 1, NULL);

-- Insert Cart Item Customizations
INSERT INTO cart_item_customizations (cart_item_id, customization_key, customization_value) VALUES
    -- Cart item 1 customizations (johndoe's ceramic mugs)
    (1, 'size', '11oz'),
    (1, 'color', 'white'),
    (1, 'print_location', 'both_sides'),
    
    -- Cart item 2 customizations (johndoe's tumbler)
    (2, 'size', '20oz'),
    (2, 'color', 'silver'),
    
    -- Cart item 3 customizations (janesmith's tote bag)
    (3, 'color', 'natural'),
    (3, 'print_location', 'front'),
    
    -- Cart item 4 customizations (janesmith's t-shirts)
    (4, 'size', 'M'),
    (4, 'color', 'black'),
    (4, 'print_location', 'front');

-- Insert Sample Orders
INSERT INTO orders (customer_id, session_id, order_number, order_status, total_amount, shipping_address, contact_phone, contact_email, notes, updated_by)
VALUES
    (1, NULL, 'ORD-00001', 'completed', 25.98, '123 Main St, Montreal, QC H1A 1A1', '514-555-0101', 'john.doe@email.com', 'Please handle with care', NULL),
    (2, NULL, 'ORD-00002', 'processing', 44.98, '456 Oak Ave, Montreal, QC H2B 2B2', '514-555-0102', 'jane.smith@email.com', NULL, 3),
    (3, NULL, 'ORD-00003', 'pending', 16.99, '789 Pine Rd, Montreal, QC H3C 3C3', '514-555-0103', 'bob.wilson@email.com', 'Rush order', NULL),
    (1, NULL, 'ORD-00004', 'cancelled', 29.98, '123 Main St, Montreal, QC H1A 1A1', '514-555-0101', 'john.doe@email.com', 'Customer changed mind', NULL),
    (4, NULL, 'ORD-00005', 'completed', 49.97, '321 Elm St, Montreal, QC H4D 4D4', '514-555-0104', 'alice.brown@email.com', NULL, NULL),
    (NULL, 'guest-checkout-abc123', 'ORD-00006', 'pending', 19.99, '555 Guest Ave, Montreal, QC H5E 5E5', '514-555-0199', 'guest@email.com', 'Guest order', NULL);

-- Insert Sample Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, design_file_url, subtotal)VALUES
    -- Order 1: Two ceramic mugs (order_id = 1)
    (1, 1, 2, 12.99, '../icons/mug.png', 25.98),

    -- Order 2: Tumbler and T-shirt (order_id = 2)
    (2, 4, 1, 24.99, '../icons/mug.png', 24.99),
    (2, 10, 1, 19.99, '../icons/mug.png', 19.99),

    -- Order 3: Canvas tote bag (order_id = 3)
    (3, 6, 1, 16.99, '../icons/mug.png', 16.99),

    -- Order 4: Cotton Shopping Bag (order_id = 4, cancelled)
    (4, 8, 2, 12.99, '../icons/mug.png', 25.98),
    (4, 1, 1, 12.99, '../icons/mug.png', 12.99),

    -- Order 5: Multiple items (order_id = 5) 
    (5, 1, 2, 14.99, '../icons/mug.png', 29.98),

    -- Order 6: Guest order (order_id = 6)
    (6, 3, 1, 19.99, '../icons/mug.png', 19.99);

-- Insert Order Item Customizations
INSERT INTO order_item_customizations (order_item_id, customization_key, customization_value) VALUES
    -- Order item 1 customizations (ceramic mugs for order 1)
    (1, 'size', '11oz'),
    (1, 'color', 'white'),
    (1, 'print_location', 'both_sides'),
    
    -- Order item 2 customizations (tumbler for order 2)
    (2, 'size', '20oz'),
    (2, 'color', 'silver'),
    
    -- Order item 3 customizations (t-shirt for order 2)
    (3, 'size', 'M'),
    (3, 'color', 'black'),
    (3, 'print_location', 'front'),
    
    -- Order item 4 customizations (tote bag for order 3)
    (4, 'color', 'natural'),
    (4, 'print_location', 'front'),
    
    -- Order item 5 customizations (shopping bags for order 4)
    (5, 'color', 'navy'),
    (5, 'print_location', 'both_sides'),
    
    -- Order item 6 customizations (ceramic mug for order 4)
    (6, 'size', '11oz'),
    (6, 'color', 'white'),
    
    -- Order item 7 customizations (t-shirt for order 5)
    (7, 'size', 'L'),
    (7, 'color', 'navy'),
    (7, 'print_location', 'back'),
    
    -- Order item 8 customizations (ceramic mugs for order 5)
    (8, 'size', '11oz'),
    (8, 'color', 'white') ;

-- Insert Sample Uploaded Files
INSERT INTO uploaded_files (customer_id, session_id, order_item_id, cart_item_id, file_url, original_filename)
VALUES
    -- Files linked to order items
    (1, NULL, 1, NULL, '../icons/mug.png', 'company_logo.png'),
    (2, NULL, 2, NULL, '../icons/mug.png', 'family_photo.jpg'),
    (2, NULL, 3, NULL, '../icons/mug.png', 'band_artwork.png'),
    (3, NULL, 4, NULL, '../icons/mug.png','business_design.pdf'),
    (1, NULL, 5, NULL, '../icons/mug.png', 'event_design.ai'),
    (1, NULL, 6, NULL, '../icons/mug.png', 'mug_design.png'),
    (4, NULL, 7, NULL, '../icons/mug.png', 'team_logo.png'),
    (4, NULL, 8, NULL, '../icons/mug.png', 'motivational_quote.jpg'), 
    
    -- Files linked to cart items (temporary)
    (1, NULL, NULL, 1, '../icons/mug.png', 'cart_logo.png'),
    (1, NULL, NULL, 2, '../icons/mug.png', 'cart_tumbler_design.jpg'),
    (2, NULL, NULL, 4, '../icons/mug.png', 'cart_tshirt_design.png'),
    (NULL, 'guest-session-12345', NULL, 5, '../icons/mug.png', 'guest_cart_design.png');

-- Insert Order Status History
INSERT INTO order_status_history (order_id, status, changed_by, notes) VALUES
    (1, 'pending', NULL, 'Order created'),
    (1, 'processing', NULL, 'Order confirmed'),
    (1, 'completed', NULL, 'Order shipped and delivered'),
    (2, 'pending', NULL, 'Order created'),
    (2, 'processing', 3, 'Order confirmed and being prepared'),
    (3, 'pending', NULL, 'Order created'),
    (4, 'pending', NULL, 'Order created'),
    (4, 'cancelled', NULL, 'Customer requested cancellation'),
    (5, 'pending', NULL, 'Order created'),
    (5, 'processing', NULL, 'Order confirmed'),
    (5, 'completed', NULL, 'Order completed'),
    (6, 'pending', NULL, 'Guest order created');

-- Insert Admin Activity Log (for the staff update action)
INSERT INTO admin_activity_log (admin_id, action, table_name, record_id, old_values, new_values, created_at) VALUES
    (2, 'add_product', 'products', 1, NULL, '{"product_name": "Ceramic Mug 11oz", "category_id": 1, "base_price": 12.99}'::jsonb, CURRENT_TIMESTAMP),
    (2, 'add_product', 'products', 2, NULL, '{"product_name": "Ceramic Mug 15oz", "category_id": 1, "base_price": 14.99}'::jsonb, CURRENT_TIMESTAMP),
    (3, 'update_order_status', 'orders', 2, '{"order_status": "pending"}'::jsonb, '{"order_status": "processing", "notes": "Order confirmed and being prepared"}'::jsonb, CURRENT_TIMESTAMP);

-- Reset sequences to match the inserted data
SELECT setval('admin_users_admin_id_seq', (SELECT MAX(admin_id) FROM admin_users));
SELECT setval('customers_customer_id_seq', (SELECT MAX(customer_id) FROM customers));
SELECT setval('categories_category_id_seq', (SELECT MAX(category_id) FROM categories));
SELECT setval('products_product_id_seq', (SELECT MAX(product_id) FROM products));
SELECT setval('shopping_carts_shopping_cart_id_seq', (SELECT MAX(shopping_cart_id) FROM shopping_carts));
SELECT setval('cart_items_cart_item_id_seq', (SELECT MAX(cart_item_id) FROM cart_items));
SELECT setval('cart_item_customizations_customization_id_seq', (SELECT MAX(customization_id) FROM cart_item_customizations));
SELECT setval('orders_order_id_seq', (SELECT MAX(order_id) FROM orders));
SELECT setval('order_items_order_item_id_seq', (SELECT MAX(order_item_id) FROM order_items));
SELECT setval('order_item_customizations_customization_id_seq', (SELECT MAX(customization_id) FROM order_item_customizations));
SELECT setval('uploaded_files_file_id_seq', (SELECT MAX(file_id) FROM uploaded_files));
SELECT setval('order_status_history_history_id_seq', (SELECT MAX(history_id) FROM order_status_history));
SELECT setval('admin_activity_log_log_id_seq', (SELECT MAX(log_id) FROM admin_activity_log));

commit;