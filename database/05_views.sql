
-- View all active shopping carts with customer info
CREATE OR REPLACE VIEW active_carts_summary AS
SELECT 
    sc.shopping_cart_id,
    c.customer_id,
    COALESCE(c.username, 'Guest') AS username,
    COALESCE(c.first_name || ' ' || c.last_name, 'Guest') AS customer_name,
    COALESCE(c.email, sc.session_id) AS cart_owner,
    c.address AS customer_address,     -- new field
    c.phone_number AS customer_phone,  -- new field
    sc.session_id,
    COUNT(ci.cart_item_id) AS item_count,
    calculate_cart_total(sc.shopping_cart_id) AS cart_total,
    sc.created_at,
    sc.updated_at,
    sc.expires_at
FROM shopping_carts sc
LEFT JOIN customers c ON sc.customer_id = c.customer_id
LEFT JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
WHERE sc.expires_at > CURRENT_TIMESTAMP
GROUP BY sc.shopping_cart_id, c.customer_id, c.username, c.first_name, c.last_name, c.email, c.address, c.phone_number, sc.session_id, sc.created_at, sc.updated_at, sc.expires_at
ORDER BY sc.updated_at DESC;

-- View cart details with products and customizations
CREATE OR REPLACE VIEW cart_details AS
SELECT 
    sc.shopping_cart_id,
    COALESCE(c.username, sc.session_id) AS cart_owner,
    cat.category_name,
    p.product_name,
    p.base_price,
    ci.quantity,
    ci.quantity * p.base_price AS line_total,
    ci.design_file_url,
    ci.added_at,
    STRING_AGG(cic.customization_key || ': ' || cic.customization_value, ', ' ORDER BY cic.customization_key) AS customizations
FROM shopping_carts sc
LEFT JOIN customers c ON sc.customer_id = c.customer_id
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN cart_item_customizations cic ON ci.cart_item_id = cic.cart_item_id
WHERE sc.expires_at > CURRENT_TIMESTAMP
GROUP BY sc.shopping_cart_id, c.username, sc.session_id, cat.category_name, p.product_name, p.base_price, ci.quantity, ci.design_file_url, ci.added_at;

-- View all orders with customer information
CREATE OR REPLACE VIEW order_summary AS
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    COALESCE(c.first_name || ' ' || c.last_name, 'Guest') AS customer_name,
    COALESCE(c.email, o.contact_email) AS email,
    COALESCE(c.address, o.shipping_address) AS shipping_address, -- use customer address if exists
    o.order_status,
    o.total_amount,
    o.created_at,
    o.updated_at,
    au.username AS updated_by_admin
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN admin_users au ON o.updated_by = au.admin_id
ORDER BY o.created_at DESC;

-- View order details with items, categories and customizations
CREATE OR REPLACE VIEW order_details AS
SELECT 
    o.order_number,
    o.order_status,
    cat.category_name,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.subtotal,
    oi.design_file_url,
    STRING_AGG(oic.customization_key || ': ' || oic.customization_value, ', ' ORDER BY oic.customization_key) AS customizations
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN order_item_customizations oic ON oi.order_item_id = oic.order_item_id
GROUP BY o.order_number, o.order_status, cat.category_name, p.product_name, oi.quantity, oi.unit_price, oi.subtotal, oi.design_file_url;

-- View products with their categories and admin who created them
CREATE OR REPLACE VIEW products_catalog AS
SELECT 
    p.product_id,
    cat.category_name,
    p.product_name,
    p.description,
    p.base_price,
    p.is_active,
    p.created_at,
    au_created.username AS created_by_admin,
    au_updated.username AS updated_by_admin
FROM products p
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN admin_users au_created ON p.created_by = au_created.admin_id
LEFT JOIN admin_users au_updated ON p.updated_by = au_updated.admin_id
WHERE p.is_active = TRUE
ORDER BY cat.display_order, p.product_name;

-- View admin activity log with details
CREATE OR REPLACE VIEW admin_activity_summary AS
SELECT 
    aal.log_id,
    au.username AS admin_username,
    au.role AS admin_role,
    aal.action,
    aal.table_name,
    aal.record_id,
    aal.old_values,
    aal.new_values,
    aal.ip_address,
    aal.created_at
FROM admin_activity_log aal
JOIN admin_users au ON aal.admin_id = au.admin_id
ORDER BY aal.created_at DESC;


COMMIT;
