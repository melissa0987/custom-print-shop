DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;

CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
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

INSERT INTO customers (id, username, email, password, first_name, last_name, phone_number, is_verified, created_at) VALUES 
    (1, 'jane_doe123', 'jane.doe@example.com', '$2a$06$L2s.dzicmhNs4unAFZP1ZOKqTxAqOsw.tkKBLDfq8TDDr8SjQb9ta', 'Jane', 'Doe', '+1-514-555-0199', TRUE, '2025-10-30 10:15:00+00'),
    (2, 'john_doe456', 'john.doe@example.com', '$2a$06$L2s.dzicmhNs4unAFZP1ZOKqTxAqOsw.tkKBLDfq8TDDr8SjQb9ta', 'John', 'Doe', '+1-514-000-0123', TRUE, '2025-10-30 10:15:00+00')

;




select * from customers;