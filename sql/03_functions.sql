
-- ============================================
-- ROLE-BASED ACCESS CONTROL FUNCTIONS
-- ============================================

-- Function to check if admin has permission for action
CREATE OR REPLACE FUNCTION has_permission(
    p_admin_id BIGINT,
    p_action VARCHAR(50)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_role VARCHAR(20);
    v_is_active BOOLEAN;
BEGIN
    -- Get admin role and active status
    SELECT role, is_active INTO v_role, v_is_active
    FROM admin_users
    WHERE admin_id = p_admin_id;
    
    -- Check if admin exists and is active
    IF v_role IS NULL OR NOT v_is_active THEN
        RETURN FALSE;
    END IF;
    
    -- Super admin can do anything
    IF v_role = 'super_admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Admin permissions
    IF v_role = 'admin' THEN
        RETURN p_action IN (
            'view_orders', 'update_order_status', 'view_customers', 
            'view_products', 'add_product', 'update_product', 
            'view_categories', 'add_category', 'update_category',
            'view_staff', 'view_reports'
        );
    END IF;
    
    -- Staff permissions (read-only + order management)
    IF v_role = 'staff' THEN
        RETURN p_action IN (
            'view_orders', 'update_order_status', 
            'view_customers', 'view_products', 'view_categories'
        );
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to log admin activity
CREATE OR REPLACE FUNCTION log_admin_activity(
    p_admin_id BIGINT,
    p_action VARCHAR(50),
    p_table_name VARCHAR(50),
    p_record_id BIGINT,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO admin_activity_log (admin_id, action, table_name, record_id, old_values, new_values, ip_address)
    VALUES (p_admin_id, p_action, p_table_name, p_record_id, p_old_values, p_new_values, p_ip_address);
END;
$$ LANGUAGE plpgsql;

-- Function for admin to add product (with permission check)
CREATE OR REPLACE FUNCTION admin_add_product(
    p_admin_id BIGINT,
    p_category_id BIGINT,
    p_product_name VARCHAR(100),
    p_description TEXT,
    p_base_price DECIMAL(10, 2)
)
RETURNS BIGINT AS $$
DECLARE
    v_product_id BIGINT;
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'add_product') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have add_product permission';
    END IF;
    
    -- Insert product
    INSERT INTO products (category_id, product_name, description, base_price, created_by, updated_by)
    VALUES (p_category_id, p_product_name, p_description, p_base_price, p_admin_id, p_admin_id)
    RETURNING product_id INTO v_product_id;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'add_product', 
        'products', 
        v_product_id,
        NULL,
        jsonb_build_object(
            'product_name', p_product_name,
            'category_id', p_category_id,
            'base_price', p_base_price
        )
    );
    
    RETURN v_product_id;
END;
$$ LANGUAGE plpgsql;

-- Function for admin to update product (with permission check)
CREATE OR REPLACE FUNCTION admin_update_product(
    p_admin_id BIGINT,
    p_product_id BIGINT,
    p_product_name VARCHAR(100) DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_base_price DECIMAL(10, 2) DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_old_values JSONB;
    v_new_values JSONB := '{}'::jsonb;
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'update_product') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have update_product permission';
    END IF;
    
    -- Get old values
    SELECT jsonb_build_object(
        'product_name', product_name,
        'description', description,
        'base_price', base_price,
        'is_active', is_active
    ) INTO v_old_values
    FROM products
    WHERE product_id = p_product_id;
    
    -- Update product
    UPDATE products
    SET 
        product_name = COALESCE(p_product_name, product_name),
        description = COALESCE(p_description, description),
        base_price = COALESCE(p_base_price, base_price),
        is_active = COALESCE(p_is_active, is_active),
        updated_at = CURRENT_TIMESTAMP,
        updated_by = p_admin_id
    WHERE product_id = p_product_id;
    
    -- Build new values JSON
    IF p_product_name IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('product_name', p_product_name);
    END IF;
    IF p_base_price IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('base_price', p_base_price);
    END IF;
    IF p_is_active IS NOT NULL THEN
        v_new_values := v_new_values || jsonb_build_object('is_active', p_is_active);
    END IF;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'update_product', 
        'products', 
        p_product_id,
        v_old_values,
        v_new_values
    );
END;
$$ LANGUAGE plpgsql;

-- Function for admin to update order status (with permission check)
CREATE OR REPLACE FUNCTION admin_update_order_status(
    p_admin_id BIGINT,
    p_order_id BIGINT,
    p_new_status VARCHAR(20),
    p_notes TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_old_status VARCHAR(20);
BEGIN
    -- Check permission
    IF NOT has_permission(p_admin_id, 'update_order_status') THEN
        RAISE EXCEPTION 'Permission denied: admin does not have update_order_status permission';
    END IF;
    
    -- Get old status
    SELECT order_status INTO v_old_status
    FROM orders
    WHERE order_id = p_order_id;
    
    -- Update order
    UPDATE orders
    SET 
        order_status = p_new_status,
        updated_at = CURRENT_TIMESTAMP,
        updated_by = p_admin_id
    WHERE order_id = p_order_id;
    
    -- Add to status history with admin info
    INSERT INTO order_status_history (order_id, status, changed_by, notes)
    VALUES (p_order_id, p_new_status, p_admin_id, p_notes);
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'update_order_status', 
        'orders', 
        p_order_id,
        jsonb_build_object('order_status', v_old_status),
        jsonb_build_object('order_status', p_new_status, 'notes', p_notes)
    );
END;
$$ LANGUAGE plpgsql;

-- Function for super admin to create admin user
CREATE OR REPLACE FUNCTION create_admin_user(
    p_creator_admin_id BIGINT,
    p_username VARCHAR(50),
    p_email VARCHAR(255),
    p_password_hash VARCHAR(255),
    p_first_name VARCHAR(100),
    p_last_name VARCHAR(100),
    p_role VARCHAR(20)
)
RETURNS BIGINT AS $$
DECLARE
    v_creator_role VARCHAR(20);
    v_new_admin_id BIGINT;
BEGIN
    -- Check if creator is super_admin
    SELECT role INTO v_creator_role
    FROM admin_users
    WHERE admin_id = p_creator_admin_id AND is_active = TRUE;
    
    IF v_creator_role != 'super_admin' THEN
        RAISE EXCEPTION 'Permission denied: only super_admin can create admin users';
    END IF;
    
    -- Insert new admin user
    INSERT INTO admin_users (username, email, password_hash, first_name, last_name, role, created_by)
    VALUES (p_username, p_email, p_password_hash, p_first_name, p_last_name, p_role, p_creator_admin_id)
    RETURNING admin_id INTO v_new_admin_id;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_creator_admin_id, 
        'create_admin_user', 
        'admin_users', 
        v_new_admin_id,
        NULL,
        jsonb_build_object(
            'username', p_username,
            'email', p_email,
            'role', p_role
        )
    );
    
    RETURN v_new_admin_id;
END;
$$ LANGUAGE plpgsql;

-- Function for super admin to deactivate admin user
CREATE OR REPLACE FUNCTION deactivate_admin_user(
    p_admin_id BIGINT,
    p_target_admin_id BIGINT
)
RETURNS VOID AS $$
DECLARE
    v_admin_role VARCHAR(20);
BEGIN
    -- Check if admin is super_admin
    SELECT role INTO v_admin_role
    FROM admin_users
    WHERE admin_id = p_admin_id AND is_active = TRUE;
    
    IF v_admin_role != 'super_admin' THEN
        RAISE EXCEPTION 'Permission denied: only super_admin can deactivate admin users';
    END IF;
    
    -- Deactivate user
    UPDATE admin_users
    SET is_active = FALSE
    WHERE admin_id = p_target_admin_id;
    
    -- Log activity
    PERFORM log_admin_activity(
        p_admin_id, 
        'deactivate_admin_user', 
        'admin_users', 
        p_target_admin_id,
        jsonb_build_object('is_active', TRUE),
        jsonb_build_object('is_active', FALSE)
    );
END;
$$ LANGUAGE plpgsql;




-- ============================================
-- OTHER FUNCTIONS 
-- ============================================

-- Function to generate order numbers
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TEXT AS $$
DECLARE
    new_order_number TEXT;
    max_number INTEGER;
BEGIN
    SELECT COALESCE(MAX(CAST(SUBSTRING(order_number FROM 5) AS INTEGER)), 0) + 1
    INTO max_number
    FROM orders;
    
    new_order_number := 'ORD-' || LPAD(max_number::TEXT, 5, '0');
    RETURN new_order_number;
END;
$$ LANGUAGE plpgsql;

-- Function to generate file path for customer uploads
CREATE OR REPLACE FUNCTION generate_customer_file_path(
    p_customer_id BIGINT,
    p_filename VARCHAR(255)
)
RETURNS TEXT AS $$
DECLARE
    v_username VARCHAR(50);
    v_timestamp TEXT;
    v_extension TEXT;
    v_base_name TEXT;
BEGIN
    -- Get customer username
    SELECT username INTO v_username
    FROM customers
    WHERE customer_id = p_customer_id;
    
    IF v_username IS NULL THEN
        RAISE EXCEPTION 'Customer not found';
    END IF;
    
    -- Generate timestamp for unique filename
    v_timestamp := TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS');
    
    -- Extract file extension
    v_extension := SUBSTRING(p_filename FROM '\.([^.]+)$');
    v_base_name := SUBSTRING(p_filename FROM '^(.+)\.[^.]+$');
    
    -- Generate path: uploads/username/basename_timestamp.ext
    RETURN 'uploads/' || v_username || '/' || v_base_name || '_' || v_timestamp || '.' || v_extension;
END;
$$ LANGUAGE plpgsql;

-- Function to generate file path for guest uploads
CREATE OR REPLACE FUNCTION generate_guest_file_path(
    p_session_id VARCHAR(255),
    p_filename VARCHAR(255)
)
RETURNS TEXT AS $$
DECLARE
    v_timestamp TEXT;
    v_extension TEXT;
    v_base_name TEXT;
BEGIN
    -- Generate timestamp for unique filename
    v_timestamp := TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS');
    
    -- Extract file extension
    v_extension := SUBSTRING(p_filename FROM '\.([^.]+)$');
    v_base_name := SUBSTRING(p_filename FROM '^(.+)\.[^.]+$');
    
    -- Generate path: uploads/guest/session_id/basename_timestamp.ext
    RETURN 'uploads/guest/' || p_session_id || '/' || v_base_name || '_' || v_timestamp || '.' || v_extension;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user can access a file
CREATE OR REPLACE FUNCTION can_access_file(
    p_file_id BIGINT,
    p_customer_id BIGINT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_file_owner_id BIGINT;
BEGIN
    SELECT customer_id INTO v_file_owner_id
    FROM uploaded_files
    WHERE file_id = p_file_id;
    
    -- Customer can only access their own files
    RETURN (v_file_owner_id = p_customer_id);
END;
$$ LANGUAGE plpgsql;

-- Function to check if admin can access file (admins can access all files)
CREATE OR REPLACE FUNCTION admin_can_access_file(
    p_file_id BIGINT,
    p_admin_id BIGINT
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Admin with view permission can access all files
    RETURN has_permission(p_admin_id, 'view_orders');
END;
$$ LANGUAGE plpgsql;

-- Function to get customer files
CREATE OR REPLACE FUNCTION get_customer_files(p_customer_id BIGINT)
RETURNS TABLE (
    file_id BIGINT,
    file_url TEXT,
    original_filename VARCHAR(255),
    file_size BIGINT,
    file_type VARCHAR(50),
    uploaded_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        uf.file_id,
        uf.file_url,
        uf.original_filename,
        uf.file_size,
        uf.file_type,
        uf.uploaded_at
    FROM uploaded_files uf
    WHERE uf.customer_id = p_customer_id
    ORDER BY uf.uploaded_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get or create cart for customer
CREATE OR REPLACE FUNCTION get_or_create_customer_cart(p_customer_id BIGINT)
RETURNS BIGINT AS $$
DECLARE
    v_cart_id BIGINT;
BEGIN
    -- Try to get existing active cart
    SELECT shopping_cart_id INTO v_cart_id
    FROM shopping_carts
    WHERE customer_id = p_customer_id
    AND expires_at > CURRENT_TIMESTAMP
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- If no cart exists, create one
    IF v_cart_id IS NULL THEN
        INSERT INTO shopping_carts (customer_id)
        VALUES (p_customer_id)
        RETURNING shopping_cart_id INTO v_cart_id;
    END IF;
    
    RETURN v_cart_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get or create cart for guest
CREATE OR REPLACE FUNCTION get_or_create_guest_cart(p_session_id VARCHAR(255))
RETURNS BIGINT AS $$
DECLARE
    v_cart_id BIGINT;
BEGIN
    -- Try to get existing active cart
    SELECT shopping_cart_id INTO v_cart_id
    FROM shopping_carts
    WHERE session_id = p_session_id
    AND expires_at > CURRENT_TIMESTAMP
    ORDER BY created_at DESC
    LIMIT 1;
    
    -- If no cart exists, create one
    IF v_cart_id IS NULL THEN
        INSERT INTO shopping_carts (session_id)
        VALUES (p_session_id)
        RETURNING shopping_cart_id INTO v_cart_id;
    END IF;
    
    RETURN v_cart_id;
END;
$$ LANGUAGE plpgsql;

-- Function to merge guest cart into customer cart after login
CREATE OR REPLACE FUNCTION merge_guest_cart_to_customer(
    p_session_id VARCHAR(255),
    p_customer_id BIGINT
)
RETURNS VOID AS $$
DECLARE
    v_guest_cart_id BIGINT;
    v_customer_cart_id BIGINT;
BEGIN
    -- Get guest cart
    SELECT shopping_cart_id INTO v_guest_cart_id
    FROM shopping_carts
    WHERE session_id = p_session_id
    AND expires_at > CURRENT_TIMESTAMP;
    
    -- If no guest cart, nothing to do
    IF v_guest_cart_id IS NULL THEN
        RETURN;
    END IF;
    
    -- Get or create customer cart
    v_customer_cart_id := get_or_create_customer_cart(p_customer_id);
    
    -- Move all items from guest cart to customer cart
    UPDATE cart_items
    SET shopping_cart_id = v_customer_cart_id
    WHERE shopping_cart_id = v_guest_cart_id;
    
    -- Update uploaded files to link to customer instead of session
    UPDATE uploaded_files
    SET customer_id = p_customer_id, session_id = NULL
    WHERE session_id = p_session_id;
    
    -- Delete the guest cart
    DELETE FROM shopping_carts WHERE shopping_cart_id = v_guest_cart_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate cart total
CREATE OR REPLACE FUNCTION calculate_cart_total(p_cart_id BIGINT)
RETURNS DECIMAL(10, 2) AS $$
DECLARE
    v_total DECIMAL(10, 2);
BEGIN
    SELECT COALESCE(SUM(ci.quantity * p.base_price), 0)
    INTO v_total
    FROM cart_items ci
    JOIN products p ON ci.product_id = p.product_id
    WHERE ci.shopping_cart_id = p_cart_id;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired carts (run periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_carts()
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM shopping_carts
    WHERE expires_at < CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Helper function to add customization to cart item
CREATE OR REPLACE FUNCTION add_cart_item_customization(
    p_cart_item_id BIGINT,
    p_key VARCHAR(100),
    p_value TEXT
)
RETURNS BIGINT AS $$
DECLARE
    v_customization_id BIGINT;
BEGIN
    INSERT INTO cart_item_customizations (cart_item_id, customization_key, customization_value)
    VALUES (p_cart_item_id, p_key, p_value)
    RETURNING customization_id INTO v_customization_id;
    
    RETURN v_customization_id;
END;
$$ LANGUAGE plpgsql;

-- Helper function to add customization to order item
CREATE OR REPLACE FUNCTION add_order_item_customization(
    p_order_item_id BIGINT,
    p_key VARCHAR(100),
    p_value TEXT
)
RETURNS BIGINT AS $$
DECLARE
    v_customization_id BIGINT;
BEGIN
    INSERT INTO order_item_customizations (order_item_id, customization_key, customization_value)
    VALUES (p_order_item_id, p_key, p_value)
    RETURNING customization_id INTO v_customization_id;
    
    RETURN v_customization_id;
END;
$$ LANGUAGE plpgsql;


COMMIT;

