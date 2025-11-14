-- optional, recommended to be run only on first setup or before deployment 
-- uncomment (delete /*   */)  to run the whole page 

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
-- DROP INDEXES
-- ============================================

-- Admin Users
DROP INDEX IF EXISTS idx_admin_users_email;
DROP INDEX IF EXISTS idx_admin_users_username;
DROP INDEX IF EXISTS idx_admin_users_role;
DROP INDEX IF EXISTS idx_admin_users_active;

-- Customers
DROP INDEX IF EXISTS idx_customers_email;
DROP INDEX IF EXISTS idx_customers_username;
DROP INDEX IF EXISTS idx_customers_active;

-- Categories
DROP INDEX IF EXISTS idx_categories_active;

-- Products
DROP INDEX IF EXISTS idx_products_category_id;
DROP INDEX IF EXISTS idx_products_active;

-- Shopping Carts
DROP INDEX IF EXISTS idx_shopping_carts_customer_id;
DROP INDEX IF EXISTS idx_shopping_carts_session_id;
DROP INDEX IF EXISTS idx_shopping_carts_expires_at;

-- Cart Items
DROP INDEX IF EXISTS idx_cart_items_shopping_cart_id;
DROP INDEX IF EXISTS idx_cart_items_product_id;

-- Cart Item Customizations
DROP INDEX IF EXISTS idx_cart_item_customizations_cart_item_id;
DROP INDEX IF EXISTS idx_cart_item_customizations_key;

-- Orders
DROP INDEX IF EXISTS idx_orders_customer_id;
DROP INDEX IF EXISTS idx_orders_session_id;
DROP INDEX IF EXISTS idx_orders_status;
DROP INDEX IF EXISTS idx_orders_order_number;

-- Order Items
DROP INDEX IF EXISTS idx_order_items_order_id;
DROP INDEX IF EXISTS idx_order_items_product_id;

-- Order Item Customizations
DROP INDEX IF EXISTS idx_order_item_customizations_order_item_id;
DROP INDEX IF EXISTS idx_order_item_customizations_key;

-- Uploaded Files
DROP INDEX IF EXISTS idx_uploaded_files_customer_id;
DROP INDEX IF EXISTS idx_uploaded_files_session_id;
DROP INDEX IF EXISTS idx_uploaded_files_order_item_id;
DROP INDEX IF EXISTS idx_uploaded_files_cart_item_id;

-- Order Status History
DROP INDEX IF EXISTS idx_order_status_history_order_id;

-- Admin Activity Log
DROP INDEX IF EXISTS idx_admin_activity_log_admin_id;
DROP INDEX IF EXISTS idx_admin_activity_log_action;
DROP INDEX IF EXISTS idx_admin_activity_log_created_at;

COMMIT;

-- ============================================
-- DROP TRIGGERS & FUNCTIONS
-- ============================================

-- ========================
-- TRIGGERS
-- ========================
DROP TRIGGER IF EXISTS update_shopping_carts_updated_at ON shopping_carts;
DROP TRIGGER IF EXISTS update_cart_on_item_insert ON cart_items;
DROP TRIGGER IF EXISTS update_cart_on_item_update ON cart_items;
DROP TRIGGER IF EXISTS update_cart_on_item_delete ON cart_items;
DROP TRIGGER IF EXISTS update_cart_items_updated_at ON cart_items;
DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;
DROP TRIGGER IF EXISTS update_products_updated_at ON products;

-- ========================
-- FUNCTIONS (TRIGGER FUNCTIONS + ADMIN FUNCTIONS)
-- ========================
DROP FUNCTION IF EXISTS update_cart_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_shopping_cart_on_item_change() CASCADE;
DROP FUNCTION IF EXISTS update_cart_item_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

DROP FUNCTION IF EXISTS get_all_admin_users(BIGINT) CASCADE;
DROP FUNCTION IF EXISTS update_admin_user(
    BIGINT,
    BIGINT,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    BOOLEAN
) CASCADE;

DROP FUNCTION IF EXISTS admin_add_category(
    BIGINT,
    VARCHAR,
    TEXT,
    INTEGER
) CASCADE;

DROP FUNCTION IF EXISTS admin_update_category(
    BIGINT,
    BIGINT,
    VARCHAR,
    TEXT,
    BOOLEAN,
    INTEGER
) CASCADE;

DROP FUNCTION IF EXISTS admin_get_customer_details(
    BIGINT,
    BIGINT
) CASCADE;

DROP FUNCTION IF EXISTS admin_get_orders(
    BIGINT,
    VARCHAR,
    INTEGER,
    INTEGER
) CASCADE;

DROP FUNCTION IF EXISTS admin_get_sales_stats(
    BIGINT,
    TIMESTAMP,
    TIMESTAMP
) CASCADE;

COMMIT;

-- Drop existing views if they exist
DROP VIEW IF EXISTS active_carts_summary CASCADE;
DROP VIEW IF EXISTS cart_details CASCADE;
DROP VIEW IF EXISTS order_summary CASCADE;
DROP VIEW IF EXISTS order_details CASCADE;
DROP VIEW IF EXISTS products_catalog CASCADE;
DROP VIEW IF EXISTS admin_activity_summary CASCADE;

COMMIT;
-- ========================================
-- DROP SCRIPT FOR OPTIONAL DATABASE ENHANCEMENTS
-- ========================================
 

-- Drop indexes (safe even if they don’t exist)
DROP INDEX IF EXISTS idx_designs_customer;
DROP INDEX IF EXISTS idx_designs_session;
DROP INDEX IF EXISTS idx_designs_product;
DROP INDEX IF EXISTS idx_designs_created;

-- Drop designs table
DROP TABLE IF EXISTS designs CASCADE;

-- ---------- OPTION D: Design Templates ----------
DROP INDEX IF EXISTS idx_design_templates_category;
DROP INDEX IF EXISTS idx_design_templates_active;
DROP TABLE IF EXISTS design_templates CASCADE;

-- ---------- OPTION E: Design Reviews ----------
DROP INDEX IF EXISTS idx_design_reviews_status;
DROP INDEX IF EXISTS idx_design_reviews_design;
DROP TABLE IF EXISTS design_reviews CASCADE;

COMMIT;

