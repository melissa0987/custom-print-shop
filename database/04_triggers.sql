
-- Trigger to automatically update shopping_carts.updated_at
CREATE OR REPLACE FUNCTION update_cart_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_shopping_carts_updated_at
BEFORE UPDATE ON shopping_carts
FOR EACH ROW
EXECUTE FUNCTION update_cart_updated_at();

-- Trigger to update shopping cart timestamp when items are modified
CREATE OR REPLACE FUNCTION update_shopping_cart_on_item_change()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE shopping_carts 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE shopping_cart_id = COALESCE(NEW.shopping_cart_id, OLD.shopping_cart_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger to update cart items INSERT
CREATE TRIGGER update_cart_on_item_insert
AFTER INSERT ON cart_items
FOR EACH ROW
EXECUTE FUNCTION update_shopping_cart_on_item_change();

-- Trigger to update cart items UPDATE
CREATE TRIGGER update_cart_on_item_update
AFTER UPDATE ON cart_items
FOR EACH ROW
EXECUTE FUNCTION update_shopping_cart_on_item_change();

CREATE TRIGGER update_cart_on_item_delete
AFTER DELETE ON cart_items
FOR EACH ROW
EXECUTE FUNCTION update_shopping_cart_on_item_change();

-- Trigger to automatically update cart_items.updated_at
CREATE OR REPLACE FUNCTION update_cart_item_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_cart_items_updated_at
BEFORE UPDATE ON cart_items
FOR EACH ROW
EXECUTE FUNCTION update_cart_item_updated_at();

-- Trigger to automatically update orders.updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger to automatically update categories.updated_at
CREATE TRIGGER update_categories_updated_at
BEFORE UPDATE ON categories
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger to automatically update products.updated_at
CREATE TRIGGER update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ADDITIONAL ADMIN MANAGEMENT FUNCTIONS
-- ============================================

-- Function to get all admin users (only for super_admin)
CREATE OR REPLACE FUNCTION get_all_admin_users(p_admin_id BIGINT)
RETURNS TABLE (
    admin_id BIGINT,
    username VARCHAR(50),
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20),
    is_active BOOLEAN,
    created_at TIMESTAMP,
    last_login TIMESTAMP
) AS $$
DECLARE
    v_role VARCHAR(20);
BEGIN
    -- Check if requester is super_admin
    SELECT role INTO v_role
    FROM admin_users
    WHERE admin_id = p_admin_id AND is_active = TRUE;
    
    IF v_role != 'super_admin' THEN
        RAISE EXCEPTION 'Permission denied: only super_admin can view all admin users';
    END IF;
    
    RETURN QUERY
    SELECT 
        au.admin_id,
        au.username,
        au.email,
        au.first_name,
        au.last_name,
        au.role,
        au.is_active,
        au.created_at,
        au.last_login
    FROM admin_users au
    ORDER BY au.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to update admin user (only super_admin)
CREATE OR REPLACE FUNCTION update_admin_user(
    p_admin_id BIGINT,
    p_target_admin_id BIGINT,
    p_email VARCHAR(255) DEFAULT NULL,
    p_first_name VARCHAR(100) DEFAULT NULL,
    p_last_name VARCHAR(100) DEFAULT NULL,
    p_role VARCHAR(20) DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_admin_role VARCHAR(20);
    v_old_values JSONB;
    v_new_values JSONB := '{}'::jsonb;
BEGIN
    -- Check if admin is super_admin
    SELECT role INTO v_admin_role
    FROM admin_users
    WHERE admin_id = p_admin_id AND is_active = TRUE;
    
    IF v_admin_role != 'super_admin' THEN
        RAISE EXCEPTION 'Permission denied: only super_admin can update admin users';
    END IF;
    
    -- Get old values
    SELECT jsonb_build_object(
        'email', email,
        'first_name', first_name,
        'last_name', last_name,
        'role', role,
        'is_active', is_active
    ) INTO v_old_values
    FROM admin_users
    WHERE admin_id = p_target_admin_id;
    
    -- Update admin user
    UPDATE admin_users
    SET 
        email = COALESCE(p_email, email),
        first_name = COALESCE(p_first_name, first_name),
        last_name = COALESCE(p_last_name, last_name),
        role = COALESCE(p_role, role),
        is_active = COALESCE(p_is_active, is_active)
    WHERE admin_id = p_target_admin_id;
    
    -- Build new values JSON
    IF p_email IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('email', p_email);
    END IF;
    IF p_role IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('role', p_role);
    END IF;
    IF p_is_active IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('is_active', p_is_active);
    END IF;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'update_admin_user', 
        'admin_users', 
        p_target_admin_id,
        v_old_values,
        v_new_values
    );
END;
$$ LANGUAGE plpgsql;

-- Function for admin to add category (with permission check)
CREATE OR REPLACE FUNCTION admin_add_category(
    p_admin_id BIGINT,
    p_category_name VARCHAR(50),
    p_description TEXT,
    p_display_order INTEGER DEFAULT 0
)
RETURNS BIGINT AS $$
DECLARE
    v_category_id BIGINT;
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'add_category') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have add_category permission';
    END IF;
    
    -- Insert category
    INSERT INTO categories (category_name, description, display_order, created_by, updated_by)
    VALUES (p_category_name, p_description, p_display_order, p_admin_id, p_admin_id)
    RETURNING category_id INTO v_category_id;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'add_category', 
        'categories', 
        v_category_id,
        NULL,
        jsonb_build_object(
            'category_name', p_category_name,
            'display_order', p_display_order
        )
    );
    
    RETURN v_category_id;
END;
$$ LANGUAGE plpgsql;

-- Function for admin to update category (with permission check)
CREATE OR REPLACE FUNCTION admin_update_category(
    p_admin_id BIGINT,
    p_category_id BIGINT,
    p_category_name VARCHAR(50) DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_display_order INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_old_values JSONB;
    v_new_values JSONB := '{}'::jsonb;
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'update_category') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have update_category permission';
    END IF;
    
    -- Get old values
    SELECT jsonb_build_object(
        'category_name', category_name,
        'description', description,
        'is_active', is_active,
        'display_order', display_order
    ) INTO v_old_values
    FROM categories
    WHERE category_id = p_category_id;
    
    -- Update category
    UPDATE categories
    SET 
        category_name = COALESCE(p_category_name, category_name),
        description = COALESCE(p_description, description),
        is_active = COALESCE(p_is_active, is_active),
        display_order = COALESCE(p_display_order, display_order),
        updated_at = CURRENT_TIMESTAMP,
        updated_by = p_admin_id
    WHERE category_id = p_category_id;
    
    -- Build new values JSON
    IF p_category_name IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('category_name', p_category_name);
    END IF;
    IF p_is_active IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('is_active', p_is_active);
    END IF;
    IF p_display_order IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('display_order', p_display_order);
    END IF;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'update_category', 
        'categories', 
        p_category_id,
        v_old_values,
        v_new_values
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get customer details (with permission check)
CREATE OR REPLACE FUNCTION admin_get_customer_details(
    p_admin_id BIGINT,
    p_customer_id BIGINT
)
RETURNS TABLE (
    customer_id BIGINT,
    username VARCHAR(50),
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    is_active BOOLEAN,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    total_orders BIGINT,
    total_spent DECIMAL(10, 2)
) AS $$
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'view_customers') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have view_customers permission';
    END IF;
    
    RETURN QUERY
    SELECT 
        c.customer_id,
        c.username,
        c.email,
        c.first_name,
        c.last_name,
        c.phone_number,
        c.is_active,
        c.created_at,
        c.last_login,
        COUNT(o.order_id) AS total_orders,
        COALESCE(SUM(CASE WHEN o.order_status = 'completed' THEN o.total_amount ELSE 0 END), 0) AS total_spent
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    WHERE c.customer_id = p_customer_id
    GROUP BY c.customer_id, c.username, c.email, c.first_name, c.last_name, c.phone_number, c.is_active, c.created_at, c.last_login;
END;
$$ LANGUAGE plpgsql;

-- Function to get all orders (with permission and filtering)
CREATE OR REPLACE FUNCTION admin_get_orders(
    p_admin_id BIGINT,
    p_status VARCHAR(20) DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    order_id BIGINT,
    order_number VARCHAR(50),
    customer_username VARCHAR(50),
    customer_email VARCHAR(255),
    order_status VARCHAR(20),
    total_amount DECIMAL(10, 2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'view_orders') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have view_orders permission';
    END IF;
    
    RETURN QUERY
    SELECT 
        o.order_id,
        o.order_number,
        COALESCE(c.username, 'Guest') AS customer_username,
        COALESCE(c.email, o.contact_email) AS customer_email,
        o.order_status,
        o.total_amount,
        o.created_at,
        o.updated_at
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    WHERE (p_status IS NULL OR o.order_status = p_status)
    ORDER BY o.created_at DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Function to get sales statistics (with permission check)
CREATE OR REPLACE FUNCTION admin_get_sales_stats(
    p_admin_id BIGINT,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
)
RETURNS TABLE (
    total_orders BIGINT,
    total_revenue DECIMAL(10, 2),
    pending_orders BIGINT,
    processing_orders BIGINT,
    completed_orders BIGINT,
    cancelled_orders BIGINT,
    average_order_value DECIMAL(10, 2)
) AS $$
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'view_reports') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have view_reports permission';
    END IF;
    
    RETURN QUERY
    SELECT 
        COUNT(*) AS total_orders,
        COALESCE(SUM(o.total_amount), 0) AS total_revenue,
        COUNT(CASE WHEN o.order_status = 'pending' THEN 1 END) AS pending_orders,
        COUNT(CASE WHEN o.order_status = 'processing' THEN 1 END) AS processing_orders,
        COUNT(CASE WHEN o.order_status = 'completed' THEN 1 END) AS completed_orders,
        COUNT(CASE WHEN o.order_status = 'cancelled' THEN 1 END) AS cancelled_orders,
        COALESCE(AVG(o.total_amount), 0) AS average_order_value
    FROM orders o
    WHERE (p_start_date IS NULL OR o.created_at >= p_start_date)
      AND (p_end_date IS NULL OR o.created_at <= p_end_date);
END;
$$ LANGUAGE plpgsql;

COMMIT;