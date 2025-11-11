
-- ============================================
-- SECTION 1: BASIC QUERIES
-- ============================================

-- 1.1 Get all active products with their categories
SELECT 
    p.product_id,
    p.product_name,
    p.description,
    p.base_price,
    c.category_name,
    p.created_at
FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE p.is_active = TRUE
ORDER BY c.display_order, p.product_name;

-- 1.2 Get all customers with their basic information
SELECT 
    customer_id,
    username,
    email,
    first_name,
    last_name,
    phone_number,
    is_active,
    created_at,
    last_login
FROM customers
WHERE is_active = TRUE
ORDER BY created_at DESC;

-- 1.3 Get all admin users with their roles
SELECT 
    admin_id,
    username,
    email,
    first_name,
    last_name,
    role,
    is_active,
    created_at,
    last_login
FROM admin_users
WHERE is_active = TRUE
ORDER BY 
    CASE role
        WHEN 'super_admin' THEN 1
        WHEN 'admin' THEN 2
        WHEN 'staff' THEN 3
    END,
    username;

-- 1.4 Get all categories ordered by display order
SELECT 
    category_id,
    category_name,
    description,
    is_active,
    display_order,
    created_at
FROM categories
WHERE is_active = TRUE
ORDER BY display_order;


-- ============================================
-- SECTION 2: SHOPPING CART QUERIES
-- ============================================

-- 2.1 Get customer's active cart with all items
SELECT 
    sc.shopping_cart_id,
    ci.cart_item_id,
    p.product_name,
    c.category_name,
    p.base_price,
    ci.quantity,
    (ci.quantity * p.base_price) AS line_total,
    ci.design_file_url,
    ci.added_at
FROM shopping_carts sc
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
WHERE sc.customer_id = 1
  AND sc.expires_at > CURRENT_TIMESTAMP
ORDER BY ci.added_at;

-- 2.2 Get cart with customizations
SELECT 
    sc.shopping_cart_id,
    ci.cart_item_id,
    p.product_name,
    ci.quantity,
    p.base_price,
    (ci.quantity * p.base_price) AS line_total,
    cic.customization_key,
    cic.customization_value
FROM shopping_carts sc
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
LEFT JOIN cart_item_customizations cic ON ci.cart_item_id = cic.cart_item_id
WHERE sc.customer_id = 1
  AND sc.expires_at > CURRENT_TIMESTAMP
ORDER BY ci.cart_item_id, cic.customization_key;

-- 2.3 Get cart total for a specific customer
SELECT 
    sc.shopping_cart_id,
    c.username,
    COUNT(ci.cart_item_id) AS total_items,
    SUM(ci.quantity) AS total_quantity,
    SUM(ci.quantity * p.base_price) AS cart_total
FROM shopping_carts sc
JOIN customers c ON sc.customer_id = c.customer_id
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
WHERE sc.customer_id = 1
  AND sc.expires_at > CURRENT_TIMESTAMP
GROUP BY sc.shopping_cart_id, c.username;

-- 2.4 Get all active carts (customer and guest)
SELECT 
    sc.shopping_cart_id,
    COALESCE(c.username, 'Guest') AS username,
    COALESCE(c.email, sc.session_id) AS identifier,
    COUNT(ci.cart_item_id) AS item_count,
    SUM(ci.quantity * p.base_price) AS cart_total,
    sc.created_at,
    sc.updated_at,
    sc.expires_at
FROM shopping_carts sc
LEFT JOIN customers c ON sc.customer_id = c.customer_id
LEFT JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
LEFT JOIN products p ON ci.product_id = p.product_id
WHERE sc.expires_at > CURRENT_TIMESTAMP
GROUP BY sc.shopping_cart_id, c.username, c.email, sc.session_id, sc.created_at, sc.updated_at, sc.expires_at
ORDER BY sc.updated_at DESC;

-- 2.5 Get expired carts (for cleanup)
SELECT 
    shopping_cart_id,
    customer_id,
    session_id,
    created_at,
    expires_at
FROM shopping_carts
WHERE expires_at < CURRENT_TIMESTAMP
ORDER BY expires_at;


-- ============================================
-- SECTION 3: ORDER QUERIES
-- ============================================

-- 3.1 Get all orders with customer information
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    COALESCE(c.first_name || ' ' || c.last_name, 'Guest') AS customer_name,
    COALESCE(c.email, o.contact_email) AS email,
    o.order_status,
    o.total_amount,
    o.shipping_address,
    o.contact_phone,
    o.created_at,
    o.updated_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
ORDER BY o.created_at DESC;

-- 3.2 Get orders by status
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    o.order_status,
    o.total_amount,
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'pending'
ORDER BY o.created_at DESC;

-- 3.3 Get specific order details with all items and customizations
SELECT 
    o.order_number,
    o.order_status,
    o.total_amount,
    o.created_at,
    oi.order_item_id,
    c.category_name,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.subtotal,
    oi.design_file_url,
    oic.customization_key,
    oic.customization_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_item_customizations oic ON oi.order_item_id = oic.order_item_id
WHERE o.order_number = 'ORD-00001'
ORDER BY oi.order_item_id, oic.customization_key;

-- 3.4 Get customer's order history
SELECT 
    o.order_id,
    o.order_number,
    o.order_status,
    o.total_amount,
    o.created_at,
    COUNT(oi.order_item_id) AS total_items,
    SUM(oi.quantity) AS total_quantity
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.customer_id = 1
GROUP BY o.order_id, o.order_number, o.order_status, o.total_amount, o.created_at
ORDER BY o.created_at DESC;

-- 3.5 Get orders within a date range
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    o.order_status,
    o.total_amount,
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE o.created_at BETWEEN '2025-10-01' AND '2025-11-30'
ORDER BY o.created_at DESC;

-- 3.6 Get order status history for a specific order
SELECT 
    osh.history_id,
    osh.status,
    osh.changed_at,
    COALESCE(au.username, 'System') AS changed_by,
    osh.notes
FROM order_status_history osh
LEFT JOIN admin_users au ON osh.changed_by = au.admin_id
WHERE osh.order_id = 1
ORDER BY osh.changed_at;

-- 3.7 Get orders with who last updated them
SELECT 
    o.order_id,
    o.order_number,
    o.order_status,
    o.total_amount,
    o.updated_at,
    au.username AS updated_by_admin,
    au.role AS admin_role
FROM orders o
LEFT JOIN admin_users au ON o.updated_by = au.admin_id
WHERE o.updated_by IS NOT NULL
ORDER BY o.updated_at DESC;


-- ============================================
-- SECTION 4: PRODUCT AND CATEGORY QUERIES
-- ============================================

-- 4.1 Get products by category
SELECT 
    p.product_id,
    p.product_name,
    p.description,
    p.base_price,
    p.is_active
FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.category_name = 'Mugs'
  AND p.is_active = TRUE
ORDER BY p.product_name;

-- 4.2 Get product count by category
SELECT 
    c.category_name,
    COUNT(p.product_id) AS total_products,
    COUNT(CASE WHEN p.is_active = TRUE THEN 1 END) AS active_products,
    COUNT(CASE WHEN p.is_active = FALSE THEN 1 END) AS inactive_products,
    AVG(p.base_price) AS avg_price,
    MIN(p.base_price) AS min_price,
    MAX(p.base_price) AS max_price
FROM categories c
LEFT JOIN products p ON c.category_id = p.category_id
GROUP BY c.category_name, c.display_order
ORDER BY c.display_order;

-- 4.3 Get most popular products (by order frequency)
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    COUNT(oi.order_item_id) AS times_ordered,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.subtotal) AS total_revenue
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name, c.category_name
ORDER BY times_ordered DESC, total_quantity_sold DESC
LIMIT 10;

-- 4.4 Get products with their creators
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.base_price,
    p.is_active,
    au_created.username AS created_by,
    p.created_at,
    au_updated.username AS last_updated_by,
    p.updated_at
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN admin_users au_created ON p.created_by = au_created.admin_id
LEFT JOIN admin_users au_updated ON p.updated_by = au_updated.admin_id
ORDER BY p.created_at DESC;

-- 4.5 Get products never ordered
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.base_price,
    p.created_at
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
WHERE oi.order_item_id IS NULL
  AND p.is_active = TRUE
ORDER BY p.created_at DESC;


-- ============================================
-- SECTION 5: FILE MANAGEMENT QUERIES
-- ============================================

-- 5.1 Get all files for a specific customer
SELECT 
    file_id,
    file_url,
    original_filename, 
    uploaded_at,
    CASE 
        WHEN order_item_id IS NOT NULL THEN 'Order'
        WHEN cart_item_id IS NOT NULL THEN 'Cart'
        ELSE 'Unassigned'
    END AS file_status
FROM uploaded_files
WHERE customer_id = 1
ORDER BY uploaded_at DESC;

-- 5.2 Get files associated with a specific order
SELECT 
    uf.file_id,
    uf.file_url,
    uf.original_filename,
    
    p.product_name,
    oi.quantity,
    uf.uploaded_at
FROM uploaded_files uf
JOIN order_items oi ON uf.order_item_id = oi.order_item_id
JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_number = 'ORD-00001'
ORDER BY oi.order_item_id;

-- 5.3 Get orphaned files (not linked to any cart or order) (no result)
SELECT 
    file_id,
    file_url,
    original_filename,
    customer_id,
    session_id,
    uploaded_at
FROM uploaded_files
WHERE order_item_id IS NULL
  AND cart_item_id IS NULL
ORDER BY uploaded_at;

-- 5.4 Get total storage used by customer
SELECT 
    c.customer_id,
    c.username,
    COUNT(uf.file_id) AS total_files
FROM customers c
LEFT JOIN uploaded_files uf ON c.customer_id = uf.customer_id
GROUP BY c.customer_id, c.username;

 


-- ============================================
-- SECTION 6: CUSTOMER ANALYTICS QUERIES
-- ============================================

-- 6.1 Get customer lifetime value
SELECT 
    c.customer_id,
    c.username,
    c.email,
    COUNT(o.order_id) AS total_orders,
    COUNT(CASE WHEN o.order_status = 'completed' THEN 1 END) AS completed_orders,
    COUNT(CASE WHEN o.order_status = 'cancelled' THEN 1 END) AS cancelled_orders,
    COALESCE(SUM(CASE WHEN o.order_status = 'completed' THEN o.total_amount ELSE 0 END), 0) AS total_spent,
    COALESCE(AVG(CASE WHEN o.order_status = 'completed' THEN o.total_amount END), 0) AS avg_order_value,
    MIN(o.created_at) AS first_order_date,
    MAX(o.created_at) AS last_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.username, c.email
ORDER BY total_spent DESC;

-- 6.2 Get top customers by order count
SELECT 
    c.customer_id,
    c.username,
    c.first_name || ' ' || c.last_name AS full_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'completed'
GROUP BY c.customer_id, c.username, c.first_name, c.last_name
ORDER BY total_orders DESC
LIMIT 10;

-- 6.3 Get customers with abandoned carts (no result so far)
SELECT 
    c.customer_id,
    c.username,
    c.email,
    sc.shopping_cart_id,
    COUNT(ci.cart_item_id) AS items_in_cart,
    SUM(ci.quantity * p.base_price) AS cart_value,
    sc.updated_at AS last_cart_update,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - sc.updated_at) AS days_since_update
FROM customers c
JOIN shopping_carts sc ON c.customer_id = sc.customer_id
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
WHERE sc.expires_at > CURRENT_TIMESTAMP
  AND NOT EXISTS (
      SELECT 1 FROM orders o 
      WHERE o.customer_id = c.customer_id 
      AND o.created_at > sc.updated_at
  )
GROUP BY c.customer_id, c.username, c.email, sc.shopping_cart_id, sc.updated_at
HAVING EXTRACT(DAY FROM CURRENT_TIMESTAMP - sc.updated_at) >= 3
ORDER BY cart_value DESC;

-- 6.4 Get new customers this month
SELECT 
    customer_id,
    username,
    email,
    first_name || ' ' || last_name AS full_name,
    created_at
FROM customers
WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
ORDER BY created_at DESC;

-- 6.5 Get customer order frequency
SELECT 
    c.customer_id,
    c.username,
    COUNT(o.order_id) AS total_orders,
    MIN(o.created_at) AS first_order,
    MAX(o.created_at) AS last_order,
    EXTRACT(DAY FROM MAX(o.created_at) - MIN(o.created_at)) AS days_between_first_and_last,
    CASE 
        WHEN COUNT(o.order_id) > 1 THEN 
            ROUND(EXTRACT(DAY FROM MAX(o.created_at) - MIN(o.created_at)) / NULLIF(COUNT(o.order_id) - 1, 0), 2)
        ELSE NULL
    END AS avg_days_between_orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.username
HAVING COUNT(o.order_id) > 0
ORDER BY total_orders DESC;


-- ============================================
-- SECTION 7: ADMIN AND AUDIT QUERIES
-- ============================================

-- 7.1 Get admin activity log with details
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
ORDER BY aal.created_at DESC
LIMIT 50;

-- 7.2 Get activity log for specific admin user
SELECT 
    aal.log_id,
    aal.action,
    aal.table_name,
    aal.record_id,
    aal.created_at,
    aal.old_values,
    aal.new_values
FROM admin_activity_log aal
WHERE aal.admin_id = 2
ORDER BY aal.created_at DESC;

-- 7.3 Get activity by action type
SELECT 
    aal.action,
    COUNT(*) AS action_count,
    COUNT(DISTINCT aal.admin_id) AS unique_admins,
    MIN(aal.created_at) AS first_occurrence,
    MAX(aal.created_at) AS last_occurrence
FROM admin_activity_log aal
GROUP BY aal.action
ORDER BY action_count DESC;

-- 7.4 Get who created/updated specific products
SELECT 
    p.product_id,
    p.product_name,
    au_created.username AS created_by,
    au_created.role AS creator_role,
    p.created_at,
    au_updated.username AS last_updated_by,
    au_updated.role AS updater_role,
    p.updated_at
FROM products p
LEFT JOIN admin_users au_created ON p.created_by = au_created.admin_id
LEFT JOIN admin_users au_updated ON p.updated_by = au_updated.admin_id
ORDER BY p.updated_at DESC;

-- 7.5 Get admin user activity summary
SELECT 
    au.admin_id,
    au.username,
    au.role,
    COUNT(aal.log_id) AS total_actions,
    COUNT(CASE WHEN aal.action LIKE '%product%' THEN 1 END) AS product_actions,
    COUNT(CASE WHEN aal.action LIKE '%order%' THEN 1 END) AS order_actions,
    COUNT(CASE WHEN aal.action LIKE '%category%' THEN 1 END) AS category_actions,
    MAX(aal.created_at) AS last_activity,
    au.last_login
FROM admin_users au
LEFT JOIN admin_activity_log aal ON au.admin_id = aal.admin_id
WHERE au.is_active = TRUE
GROUP BY au.admin_id, au.username, au.role, au.last_login
ORDER BY total_actions DESC;


-- ============================================
-- SECTION 8: SALES AND REVENUE QUERIES
-- ============================================

-- 8.1 Get sales summary by status
SELECT 
    order_status,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value,
    MIN(total_amount) AS min_order_value,
    MAX(total_amount) AS max_order_value
FROM orders
GROUP BY order_status
ORDER BY 
    CASE order_status
        WHEN 'completed' THEN 1
        WHEN 'processing' THEN 2
        WHEN 'pending' THEN 3
        WHEN 'cancelled' THEN 4
    END;

-- 8.2 Get daily sales (last 30 days)
SELECT 
    DATE(created_at) AS order_date,
    COUNT(*) AS orders_count,
    SUM(total_amount) AS daily_revenue,
    AVG(total_amount) AS avg_order_value
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
  AND order_status = 'completed'
GROUP BY DATE(created_at)
ORDER BY order_date DESC;

-- 8.3 Get monthly sales summary
SELECT 
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS total_orders,
    COUNT(CASE WHEN order_status = 'completed' THEN 1 END) AS completed_orders,
    SUM(CASE WHEN order_status = 'completed' THEN total_amount ELSE 0 END) AS revenue,
    AVG(CASE WHEN order_status = 'completed' THEN total_amount END) AS avg_order_value
FROM orders
WHERE created_at >= DATE_TRUNC('year', CURRENT_DATE)
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- 8.4 Get revenue by category
SELECT 
    c.category_name,
    COUNT(DISTINCT o.order_id) AS orders_with_category,
    SUM(oi.quantity) AS total_units_sold,
    SUM(oi.subtotal) AS total_revenue,
    AVG(oi.unit_price) AS avg_unit_price
FROM categories c
JOIN products p ON c.category_id = p.category_id
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_status = 'completed'
GROUP BY c.category_name, c.display_order
ORDER BY total_revenue DESC;

-- 8.5 Get revenue by product
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    COUNT(oi.order_item_id) AS times_sold,
    SUM(oi.quantity) AS total_quantity,
    SUM(oi.subtotal) AS total_revenue,
    AVG(oi.unit_price) AS avg_selling_price,
    p.base_price AS current_base_price
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id AND o.order_status = 'completed'
GROUP BY p.product_id, p.product_name, c.category_name, p.base_price
ORDER BY total_revenue DESC NULLS LAST;

-- 8.6 Get conversion rate (orders vs carts)
SELECT 
    COUNT(DISTINCT sc.shopping_cart_id) AS total_carts,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(
        COUNT(DISTINCT o.order_id)::NUMERIC / 
        NULLIF(COUNT(DISTINCT sc.shopping_cart_id), 0) * 100, 
        2
    ) AS conversion_rate_percent
FROM shopping_carts sc
LEFT JOIN orders o ON sc.customer_id = o.customer_id
WHERE sc.created_at >= CURRENT_DATE - INTERVAL '30 days';


-- ============================================
-- SECTION 9: ADVANCED ANALYTICS QUERIES
-- ============================================

-- 9.1 Get customer cohort analysis (by month joined)
SELECT 
    DATE_TRUNC('month', c.created_at) AS cohort_month,
    COUNT(DISTINCT c.customer_id) AS customers_in_cohort,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS customers_who_ordered,
    ROUND(
        COUNT(DISTINCT o.customer_id)::NUMERIC / 
        NULLIF(COUNT(DISTINCT c.customer_id), 0) * 100, 
        2
    ) AS order_rate_percent,
    SUM(o.total_amount) AS total_revenue
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'completed'
GROUP BY DATE_TRUNC('month', c.created_at)
ORDER BY cohort_month DESC;

-- 9.2 Get repeat customer rate
SELECT 
    COUNT(DISTINCT customer_id) AS total_customers_with_orders,
    COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) AS repeat_customers,
    ROUND(
        COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END)::NUMERIC / 
        NULLIF(COUNT(DISTINCT customer_id), 0) * 100, 
        2
    ) AS repeat_customer_rate_percent
FROM (
    SELECT 
        customer_id,
        COUNT(*) AS order_count
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
) AS customer_orders;

-- 9.3 Get average order value by customer type (repeat vs one-time)
SELECT 
    CASE 
        WHEN order_count = 1 THEN 'One-time Customer'
        WHEN order_count BETWEEN 2 AND 5 THEN 'Repeat Customer (2-5 orders)'
        ELSE 'Loyal Customer (5+ orders)'
    END AS customer_type,
    COUNT(DISTINCT customer_id) AS customer_count,
    SUM(total_spent) AS total_revenue,
    ROUND(AVG(avg_order_value), 2) AS avg_order_value,
    ROUND(AVG(total_spent), 2) AS avg_customer_lifetime_value
FROM (
    SELECT 
        customer_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS total_spent,
        AVG(total_amount) AS avg_order_value
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
) AS customer_stats
GROUP BY 
    CASE 
        WHEN order_count = 1 THEN 'One-time Customer'
        WHEN order_count BETWEEN 2 AND 5 THEN 'Repeat Customer (2-5 orders)'
        ELSE 'Loyal Customer (5+ orders)'
    END
ORDER BY customer_count DESC;

-- 9.4 Get order fulfillment time analysis
SELECT 
    o.order_id,
    o.order_number,
    o.created_at AS order_created,
    MIN(CASE WHEN osh.status = 'processing' THEN osh.changed_at END) AS processing_started,
    MIN(CASE WHEN osh.status = 'completed' THEN osh.changed_at END) AS completed_at,
    EXTRACT(HOUR FROM 
        MIN(CASE WHEN osh.status = 'completed' THEN osh.changed_at END) - o.created_at
    ) AS hours_to_complete
FROM orders o
JOIN order_status_history osh ON o.order_id = osh.order_id
WHERE o.order_status = 'completed'
GROUP BY o.order_id, o.order_number, o.created_at
ORDER BY o.created_at DESC;

-- 9.5 Get cart abandonment analysis
SELECT 
    DATE(sc.created_at) AS cart_date,
    COUNT(DISTINCT sc.shopping_cart_id) AS carts_created,
    COUNT(DISTINCT CASE 
        WHEN EXISTS (
            SELECT 1 FROM orders o 
            WHERE o.customer_id = sc.customer_id 
            AND o.created_at > sc.created_at 
            AND o.created_at < sc.created_at + INTERVAL '1 day'
        ) THEN sc.shopping_cart_id 
    END) AS carts_converted_to_orders,
    ROUND(
        COUNT(DISTINCT CASE 
            WHEN EXISTS (
                SELECT 1 FROM orders o 
                WHERE o.customer_id = sc.customer_id 
                AND o.created_at > sc.created_at 
                AND o.created_at < sc.created_at + INTERVAL '1 day'
            ) THEN sc.shopping_cart_id 
        END)::NUMERIC / 
        NULLIF(COUNT(DISTINCT sc.shopping_cart_id), 0) * 100, 
        2
    ) AS conversion_rate_percent
FROM shopping_carts sc
WHERE sc.created_at >= CURRENT_DATE - INTERVAL '30 days'
  AND sc.customer_id IS NOT NULL
GROUP BY DATE(sc.created_at)
ORDER BY cart_date DESC;


-- ============================================
-- SECTION 10: SEARCH AND FILTER QUERIES
-- ============================================

-- 10.1 Search products by name or description
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    p.description,
    p.base_price
FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE p.is_active = TRUE
  AND (
      p.product_name ILIKE '%mug%'
      OR p.description ILIKE '%mug%'
  )
ORDER BY p.product_name;

-- 10.2 Search orders by order number, customer name, or email
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    COALESCE(c.first_name || ' ' || c.last_name, 'Guest') AS customer_name,
    COALESCE(c.email, o.contact_email) AS email,
    o.order_status,
    o.total_amount,
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_number ILIKE '%001%'
   OR c.username ILIKE '%john%'
   OR c.email ILIKE '%john%'
   OR o.contact_email ILIKE '%john%'
ORDER BY o.created_at DESC;

-- 10.3 Filter orders by date range and status
SELECT 
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    o.order_status,
    o.total_amount,
    o.created_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE o.created_at BETWEEN '2025-10-01' AND '2025-10-31'
  AND o.order_status IN ('completed', 'processing')
ORDER BY o.created_at DESC;

-- 10.4 Find customers by name, email, or username
SELECT 
    customer_id,
    username,
    email,
    first_name || ' ' || last_name AS full_name,
    phone_number,
    created_at
FROM customers
WHERE username ILIKE '%john%'
   OR email ILIKE '%john%'
   OR first_name ILIKE '%john%'
   OR last_name ILIKE '%john%'
ORDER BY created_at DESC;

-- 10.5 Get orders with specific product
SELECT DISTINCT
    o.order_id,
    o.order_number,
    COALESCE(c.username, 'Guest') AS username,
    o.order_status,
    o.total_amount,
    o.created_at,
    oi.quantity AS product_quantity,
    oi.unit_price AS product_price
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE p.product_name ILIKE '%Ceramic Mug%'
ORDER BY o.created_at DESC;


-- ============================================
-- SECTION 11: USING VIEWS
-- ============================================

-- 11.1 Query active carts summary view
SELECT * FROM active_carts_summary
WHERE item_count > 0
ORDER BY cart_total DESC;

-- 11.2 Query cart details view
SELECT * FROM cart_details
WHERE cart_owner = 'johndoe'
ORDER BY added_at DESC;

-- 11.3 Query order summary view
SELECT * FROM order_summary
WHERE order_status = 'pending'
ORDER BY created_at DESC;

-- 11.4 Query order details view
SELECT * FROM order_details
WHERE order_number = 'ORD-00001';

-- 11.5 Query products catalog view
SELECT * FROM products_catalog
WHERE category_name = 'Mugs'
ORDER BY product_name;

-- 11.6 Query admin activity summary view
SELECT * FROM admin_activity_summary
WHERE action LIKE '%product%'
ORDER BY created_at DESC
LIMIT 20;


-- ============================================
-- SECTION 12: COMPLEX JOINS AND SUBQUERIES
-- ============================================

-- 12.1 Get customers who never placed an order
SELECT 
    c.customer_id,
    c.username,
    c.email,
    c.created_at,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - c.created_at) AS days_since_signup
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
  AND c.is_active = TRUE
ORDER BY c.created_at DESC;

-- 12.2 Get products in cart but never ordered
SELECT DISTINCT
    p.product_id,
    p.product_name,
    c.category_name,
    COUNT(DISTINCT ci.shopping_cart_id) AS times_added_to_cart
FROM products p
JOIN categories c ON p.category_id = c.category_id
JOIN cart_items ci ON p.product_id = ci.product_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
WHERE oi.order_item_id IS NULL
GROUP BY p.product_id, p.product_name, c.category_name
ORDER BY times_added_to_cart DESC;

-- 12.3 Get customers with high cart value but no recent orders
SELECT 
    c.customer_id,
    c.username,
    c.email,
    SUM(ci.quantity * p.base_price) AS current_cart_value,
    MAX(o.created_at) AS last_order_date,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - MAX(o.created_at)) AS days_since_last_order
FROM customers c
JOIN shopping_carts sc ON c.customer_id = sc.customer_id
JOIN cart_items ci ON sc.shopping_cart_id = ci.shopping_cart_id
JOIN products p ON ci.product_id = p.product_id
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE sc.expires_at > CURRENT_TIMESTAMP
GROUP BY c.customer_id, c.username, c.email
HAVING SUM(ci.quantity * p.base_price) > 50
   AND (MAX(o.created_at) < CURRENT_DATE - INTERVAL '30 days' OR MAX(o.created_at) IS NULL)
ORDER BY current_cart_value DESC;

-- 12.4 Get order items with their customizations (pivot-style)
SELECT 
    oi.order_item_id,
    o.order_number,
    p.product_name,
    oi.quantity,
    MAX(CASE WHEN oic.customization_key = 'size' THEN oic.customization_value END) AS size,
    MAX(CASE WHEN oic.customization_key = 'color' THEN oic.customization_value END) AS color,
    MAX(CASE WHEN oic.customization_key = 'print_location' THEN oic.customization_value END) AS print_location
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN order_item_customizations oic ON oi.order_item_id = oic.order_item_id
WHERE o.order_number = 'ORD-00001'
GROUP BY oi.order_item_id, o.order_number, p.product_name, oi.quantity;

-- 12.5 Get ranking of products by revenue
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    COALESCE(SUM(oi.subtotal), 0) AS total_revenue,
    RANK() OVER (ORDER BY COALESCE(SUM(oi.subtotal), 0) DESC) AS revenue_rank,
    DENSE_RANK() OVER (PARTITION BY c.category_id ORDER BY COALESCE(SUM(oi.subtotal), 0) DESC) AS category_rank
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id AND o.order_status = 'completed'
GROUP BY p.product_id, p.product_name, c.category_name, c.category_id
ORDER BY revenue_rank;


SELECT username, password_hash FROM customers WHERE username='johndoe';