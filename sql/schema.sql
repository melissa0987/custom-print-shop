-- ============================================
-- Custom Printing Website Database Schema
-- PostgreSQL Script (WITH STAFF/ADMIN & ROLE-BASED ACCESS) 
-- ============================================

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS admin_activity_log CASCADE;
DROP TABLE IF EXISTS order_status_history CASCADE;
DROP TABLE IF EXISTS order_item_customizations CASCADE;
DROP TABLE IF EXISTS cart_item_customizations CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS uploaded_files CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS shopping_carts CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS admin_users CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================
-- 1. Admin_Users Table 
-- ============================================
CREATE TABLE admin_users (
    admin_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('super_admin', 'admin', 'staff')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    CONSTRAINT chk_admin_username_format CHECK (username ~* '^[a-z0-9_-]{3,50}$')
);


-- ============================================
-- 2. Customers Table
-- ============================================
CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT chk_username_format CHECK (username ~* '^[a-z0-9_-]{3,50}$')
);
 

-- ============================================
-- 3. Categories Table 
-- ============================================
CREATE TABLE categories (
    category_id BIGSERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL
); 

 
-- ============================================
-- 4. Products Table
-- ============================================
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL CHECK (base_price >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL
);
 

-- ============================================
-- 5. Shopping_Carts Table
-- ============================================
CREATE TABLE shopping_carts (
    shopping_cart_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(customer_id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 days'),
    CONSTRAINT chk_cart_owner CHECK (
        (customer_id IS NOT NULL AND session_id IS NULL) OR 
        (customer_id IS NULL AND session_id IS NOT NULL)
    )
);


-- ============================================
-- 6. Cart_Items Table
-- ============================================
CREATE TABLE cart_items (
    cart_item_id BIGSERIAL PRIMARY KEY,
    shopping_cart_id BIGINT NOT NULL REFERENCES shopping_carts(shopping_cart_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    design_file_url TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
 

-- ============================================
-- 7. Cart_Item_Customizations Table
-- ============================================
CREATE TABLE cart_item_customizations (
    customization_id BIGSERIAL PRIMARY KEY,
    cart_item_id BIGINT NOT NULL REFERENCES cart_items(cart_item_id) ON DELETE CASCADE,
    customization_key VARCHAR(100) NOT NULL,
    customization_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

 

-- ============================================
-- 8. Orders Table
-- ============================================
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(customer_id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (order_status IN ('pending', 'processing', 'completed', 'cancelled')),
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    shipping_address TEXT NOT NULL,
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL
);



-- ============================================
-- 9. Order_Items Table
-- ============================================
CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    design_file_url TEXT,
    subtotal DECIMAL(10, 2) NOT NULL CHECK (subtotal >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

 

-- ============================================
-- 10. Order_Item_Customizations Table
-- ============================================
CREATE TABLE order_item_customizations (
    customization_id BIGSERIAL PRIMARY KEY,
    order_item_id BIGINT NOT NULL REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    customization_key VARCHAR(100) NOT NULL,
    customization_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
 

-- ============================================
-- 11. Uploaded_Files Table
-- ============================================
CREATE TABLE uploaded_files (
    file_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(customer_id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    order_item_id BIGINT REFERENCES order_items(order_item_id) ON DELETE SET NULL,
    cart_item_id BIGINT REFERENCES cart_items(cart_item_id) ON DELETE SET NULL,
    file_url TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(50),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_file_owner CHECK (
        (customer_id IS NOT NULL AND session_id IS NULL) OR 
        (customer_id IS NULL AND session_id IS NOT NULL)
    )
);


-- ============================================
-- 12. Order_Status_History Table
-- ============================================
CREATE TABLE order_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'cancelled')),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by BIGINT REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    notes TEXT
);




-- ============================================
-- 13. Admin_Activity_Log Table (NEW - for audit trail)
-- ============================================
CREATE TABLE admin_activity_log (
    log_id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL REFERENCES admin_users(admin_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50),
    record_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



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


COMMIT;

