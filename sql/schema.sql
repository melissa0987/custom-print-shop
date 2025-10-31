
--================ DROP TABLES STATEMENTS ================

DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS product_variants CASCADE;

--================ CREATE TABLES STATEMENTS ================
--1. Customers Table
CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--2. Addresses Table
CREATE TABLE addresses (
    address_id  BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    address_type VARCHAR(20) CHECK (address_type IN ('billing', 'shipping')) NOT NULL,
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--3. Product_Categories Table
CREATE TABLE product_categories (
    category_id BIGSERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT, 
    is_active BOOLEAN DEFAULT TRUE
);

--4. Products Table
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES product_categories(category_id) ON DELETE CASCADE,
    product_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    sku VARCHAR(50),
    stock_amount INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
--5. Product_Variants Table
CREATE TABLE product_variants (
    variant_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    variant_type VARCHAR(50) NOT NULL,       
    variant_value VARCHAR(100) NOT NULL,    
    price_modifier DECIMAL(10,2) DEFAULT 0.00,
    stock_quantity INT DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE
);

--6. Printing_Options Table
--7. Design_Templates Table
--8. Orders Table
--9. Order_Items Table
--10. Uploaded_Designs Table
--11. Price_Tiers Table
--12. Order_Status_History Table
--13. Product_Specifications Table
--14. Reviews Table
--15. Shopping_Cart Table
--16. Cart_Items Table
--17. Discount_Codes Table
--18. Admin_Users Table
--19. Production_Queue Table
--================ INSERT TABLES STATEMENTS ================

INSERT INTO customers (customer_id, username, email, password, first_name, last_name, phone_number, is_verified, created_at) VALUES 
    (1, 'jane_doe123', 'jane.doe@example.com', '$2a$06$L2s.dzicmhNs4unAFZP1ZOKqTxAqOsw.tkKBLDfq8TDDr8SjQb9ta', 'Jane', 'Doe', '+1-514-555-0199', TRUE, '2025-10-30 10:15:00+00'),
    (2, 'john_doe456', 'john.doe@example.com', '$2a$06$L2s.dzicmhNs4unAFZP1ZOKqTxAqOsw.tkKBLDfq8TDDr8SjQb9ta', 'John', 'Doe', '+1-514-000-0123', TRUE, '2025-10-30 10:15:00+00')
;

INSERT INTO addresses (address_id, customer_id, address_type, street_address, city, state_province, postal_code, country, is_default) VALUES 
    (1, 1,'billing', '123 Maple Avenue', 'Montreal', 'Quebec', 'H3Z 2Y7', 'Canada', TRUE),
    (2, 2, 'shipping', '456 King Street West', 'Toronto', 'Ontario', 'M5V 1L7','Canada', FALSE)
;

INSERT INTO product_categories (category_id, category_name, description, is_active) VALUES 
    (1, 'Mugs', 'Custom printed ceramic mugs for any occasion.',  TRUE),
    (2, 'Tumbler', 'Personalized stainless steel tumblers for hot and cold drinks.', TRUE),
    (3, 'Bag', 'Custom tote bags and backpacks with printed designs.',  TRUE),
    (4, 'T-Shirt', 'Printed t-shirts in various styles, colors, and sizes.',  TRUE)
;
INSERT INTO products (product_id, category_id, product_name, description, base_price, sku, stock_amount) VALUES
    (1, 1, 'Classic White Mug', '11oz ceramic mug with custom logo printing.', 9.99, 'MUG-001', 2),
    (2, 1, 'Large Coffee Mug', '15oz ceramic mug with full-color printing.', 12.49, 'MUG-002', 3),
    (3, 2, 'Stainless Steel Tumbler', '20oz insulated tumbler, keeps drinks hot or cold.', 19.99, 'TUMBLER-001', 5),
    (4, 3, 'Canvas Tote Bag', 'Durable canvas tote bag with printed design.', 14.99, 'BAG-001', 2),
    (5, 3, 'Backpack', 'Stylish backpack with custom print and multiple compartments.', 29.99, 'BAG-002', 7),
    (6, 4, 'Crew Neck T-Shirt', 'Soft cotton t-shirt with full-color print.', 19.99, 'TSHIRT-001', 5),
    (7, 4, 'V-Neck T-Shirt', 'Lightweight v-neck t-shirt for casual wear.', 21.99, 'TSHIRT-002', 3)
;

    -- Product Variants for Mugs (category_id = 1)
    INSERT INTO product_variants (variant_id, product_id, variant_type, variant_value, price_modifier, stock_quantity, is_available) VALUES
    (1, 1, 'size', '11oz', 0.00, 150, TRUE),
    (2, 1, 'size', '15oz', 2.50, 100, TRUE),
    (3, 2, 'color', 'White', 0.00, 120, TRUE),
    (4, 2, 'color', 'Black', 0.50, 90, TRUE);

    -- Product Variants for Tumblers (category_id = 2)
    INSERT INTO product_variants (product_id, variant_type, variant_value, price_modifier, stock_quantity, is_available) VALUES
    (3, 'size', '20oz', 0.00, 200, TRUE),
    (3, 'size', '30oz', 3.00, 120, TRUE),
    (3, 'material', 'Stainless Steel', 0.00, 200, TRUE);

    -- Product Variants for Bags (category_id = 3)
    INSERT INTO product_variants (product_id, variant_type, variant_value, price_modifier, stock_quantity, is_available) VALUES
    (4, 'type', 'Canvas Tote', 0.00, 150, TRUE),
    (4, 'type', 'Drawstring Bag', 1.50, 90, TRUE),
    (5, 'color', 'Natural', 0.00, 100, TRUE),
    (5, 'color', 'Black', 0.75, 80, TRUE);

    -- Product Variants for T-Shirts (category_id = 4)
    INSERT INTO product_variants (product_id, variant_type, variant_value, price_modifier, stock_quantity, is_available) VALUES
    (6, 'size', 'Small', 0.00, 60, TRUE),
    (6, 'size', 'Medium', 0.00, 80, TRUE),
    (6, 'size', 'Large', 1.50, 50, TRUE),
    (6, 'color', 'White', 0.00, 70, TRUE),
    (6, 'color', 'Black', 0.50, 65, TRUE),
    (7, 'size', 'Medium', 0.00, 40, TRUE),
    (7, 'size', 'Large', 1.00, 35, TRUE);

--================ SELECT STATEMENTS ================
select * from customers;
select * from addresses;
select * from product_categories;
select * from products;

