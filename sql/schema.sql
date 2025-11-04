-- ============================================
-- Custom Printing Website Database Schema
-- PostgreSQL Script
-- ============================================

-- Drop tables if they exist (for clean setup)

DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS orders CASCADE;

-- ============================================
-- 1. Customers Table
-- ============================================
CREATE TABLE customers  (
    customer_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. Categories Table 
-- ============================================
CREATE TABLE categories (
    category_id BIGSERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 

-- ============================================
-- 3. Products Table
-- ============================================
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL CHECK (base_price >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 4. Orders Table
-- ============================================
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (order_status IN ('pending', 'processing', 'completed', 'cancelled')),
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    shipping_address TEXT NOT NULL,
    contact_phone VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FUNCTIONS FOR GENERATING ORDER NUMBERS
-- ============================================
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


-- ============================================
-- SAMPLE DATA
-- ============================================

-- Insert Sample Customers
INSERT INTO customers (customer_id, email, password_hash, first_name, last_name, phone_number) VALUES
    (1, 'john.doe@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2LZb9qL.bS', 'John', 'Doe', '514-555-0101'),
    (2, 'jane.smith@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2LZb9qL.bS', 'Jane', 'Smith', '514-555-0102'),
    (3, 'bob.wilson@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2LZb9qL.bS', 'Bob', 'Wilson', '514-555-0103'),
    (4, 'alice.brown@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2LZb9qL.bS', 'Alice', 'Brown', '514-555-0104'),
    (5, 'charlie.davis@email.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2LZb9qL.bS', 'Charlie', 'Davis', '514-555-0105');

-- Insert Categories
INSERT INTO categories (category_id, category_name, description, is_active) VALUES
    (1, 'Mugs', 'Ceramic and insulated mugs for hot and cold beverages', TRUE),
    (2, 'Tumblers', 'Insulated stainless steel tumblers', TRUE),
    (3, 'Bags', 'Tote bags, drawstring bags, and shopping bags', TRUE),
    (4, 'T-Shirts', 'Custom printed t-shirts in various sizes', TRUE)
    ;


-- Insert Sample Products 
INSERT INTO products (product_id, category_id, product_name, description, base_price, is_active) VALUES
    -- Mugs (category_id = 1)
    (1, 1, 'Ceramic Mug 11oz', 'Classic white ceramic mug, dishwasher safe', 12.99, TRUE),
    (2, 1, 'Ceramic Mug 15oz', 'Large ceramic mug, perfect for coffee lovers', 14.99, TRUE),
    (3, 1, 'Travel Mug', 'Insulated stainless steel travel mug with lid', 19.99, TRUE),

    -- Tumblers (category_id = 2)
    (4, 2, 'Stainless Tumbler 20oz', 'Double-wall insulated tumbler', 24.99, TRUE),
    (5, 2, 'Stainless Tumbler 30oz', 'Large insulated tumbler with straw', 29.99, TRUE),

    -- Bags (category_id = 3)
    (6, 3, 'Canvas Tote Bag', 'Durable canvas tote bag, 15x16 inches', 16.99, TRUE),
    (7, 3, 'Cotton Drawstring Bag', 'Lightweight cotton drawstring bag', 9.99, TRUE),
    (8, 3, 'Cotton Shopping Bag', 'Reusable cotton shopping bag with handles', 12.99, TRUE),

    -- T-Shirts (category_id = 4)
    (9, 4, 'Cotton T-Shirt - S', 'Premium 100% cotton t-shirt, size Small', 19.99, TRUE),
    (10, 4, 'Cotton T-Shirt - M', 'Premium 100% cotton t-shirt, size Medium', 19.99, TRUE),
    (11, 4, 'Cotton T-Shirt - L', 'Premium 100% cotton t-shirt, size Large', 19.99, TRUE),
    (12, 4, 'Cotton T-Shirt - XL', 'Premium 100% cotton t-shirt, size XL', 19.99, TRUE)
;

-- Insert Sample Orders
INSERT INTO orders (order_id, customer_id, order_number, order_status, total_amount, shipping_address, contact_phone, notes)
VALUES
(1, 1, generate_order_number(), 'completed', 27.98, '123 Main St, Montreal, QC H1A 1A1', '514-555-0101', 'Please handle with care'),
(2, 2, generate_order_number(), 'processing', 44.98, '456 Oak Ave, Montreal, QC H2B 2B2', '514-555-0102', NULL),
(3, 3, generate_order_number(), 'pending', 19.99, '789 Pine Rd, Montreal, QC H3C 3C3', '514-555-0103', 'Rush order'),
(4, 1, generate_order_number(), 'cancelled', 49.99, '123 Main St, Montreal, QC H1A 1A1', '514-555-0101', 'Customer changed mind'),
(5, 4, generate_order_number(), 'completed', 54.97, '321 Elm St, Montreal, QC H4D 4D4', '514-555-0104', NULL);


-- SELECT  statements 
SELECT * FROM customers;
SELECT * FROM categories;
SELECT * FROM products;
SELECT * FROM orders;

COMMIT;