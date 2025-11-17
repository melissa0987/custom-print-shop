-- ========================================
-- OPTIONAL DATABASE ENHANCEMENTS
-- Only run these if you want additional features
-- ========================================

-- Option A: Add design positioning to uploaded_files
-- (For future drag/resize/rotate features)
ALTER TABLE uploaded_files
ADD COLUMN design_scale DECIMAL(3,2) DEFAULT 0.50,  -- Size: 0.10 to 1.00
ADD COLUMN design_x DECIMAL(3,2) DEFAULT 0.50,      -- Position X: 0.00 to 1.00
ADD COLUMN design_y DECIMAL(3,2) DEFAULT 0.50,      -- Position Y: 0.00 to 1.00
ADD COLUMN design_rotation INTEGER DEFAULT 0,        -- Rotation: 0 to 359 degrees
ADD COLUMN preview_url TEXT;                         -- Store preview URL separately

COMMENT ON COLUMN uploaded_files.design_scale IS 'Design size relative to mockup (0.10-1.00)';
COMMENT ON COLUMN uploaded_files.design_x IS 'Horizontal position (0.00=left, 0.50=center, 1.00=right)';
COMMENT ON COLUMN uploaded_files.design_y IS 'Vertical position (0.00=top, 0.50=center, 1.00=bottom)';
COMMENT ON COLUMN uploaded_files.design_rotation IS 'Rotation in degrees (0-359)';
COMMENT ON COLUMN uploaded_files.preview_url IS 'URL to preview image with design on mockup';


-- Option B: Add product mockup configuration
-- (For managing different mockup images per product)
ALTER TABLE products
ADD COLUMN mockup_image_url TEXT,                   -- Path to mockup image
ADD COLUMN mockup_design_area JSONB;                -- Design placement area definition

COMMENT ON COLUMN products.mockup_image_url IS 'Path to product mockup image file';
COMMENT ON COLUMN products.mockup_design_area IS 'JSON config for design placement: {"x": 0.5, "y": 0.5, "maxScale": 0.6}';

-- Example mockup_design_area value:
-- {
--   "x": 0.5,           -- Center horizontally
--   "y": 0.5,           -- Center vertically  
--   "maxScale": 0.6,    -- Max 60% of mockup size
--   "minScale": 0.2,    -- Min 20% of mockup size
--   "allowRotation": true
-- }


-- Option C: Create a dedicated designs table
-- (For better organization if you expect many designs per user)
CREATE TABLE IF NOT EXISTS designs (
    design_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) ON DELETE SET NULL,
    session_id VARCHAR(100),
    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
    
    -- File information
    design_url TEXT NOT NULL,
    preview_url TEXT,
    original_filename VARCHAR(255),
    file_size INTEGER,                              -- Size in bytes
    
    -- Image information
    image_width INTEGER,
    image_height INTEGER,
    image_format VARCHAR(10),
    
    -- Design positioning
    design_scale DECIMAL(3,2) DEFAULT 0.50,
    design_x DECIMAL(3,2) DEFAULT 0.50,
    design_y DECIMAL(3,2) DEFAULT 0.50,
    design_rotation INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CHECK (design_scale >= 0.10 AND design_scale <= 1.00),
    CHECK (design_x >= 0.00 AND design_x <= 1.00),
    CHECK (design_y >= 0.00 AND design_y <= 1.00),
    CHECK (design_rotation >= 0 AND design_rotation < 360),
    CHECK (customer_id IS NOT NULL OR session_id IS NOT NULL)
);

-- Indexes for the designs table
CREATE INDEX idx_designs_customer ON designs(customer_id);
CREATE INDEX idx_designs_session ON designs(session_id);
CREATE INDEX idx_designs_product ON designs(product_id);
CREATE INDEX idx_designs_created ON designs(created_at DESC);

-- Then modify cart_items and order_items to reference designs
ALTER TABLE cart_items
ADD COLUMN design_id INTEGER REFERENCES designs(design_id) ON DELETE SET NULL;

ALTER TABLE order_items
ADD COLUMN design_id INTEGER REFERENCES designs(design_id) ON DELETE SET NULL;


-- Option D: Add design templates/presets
-- (For offering pre-made designs to users)
CREATE TABLE IF NOT EXISTS design_templates (
    template_id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    template_category VARCHAR(50),
    
    -- Template file
    template_url TEXT NOT NULL,
    thumbnail_url TEXT,
    
    -- Applicable products
    product_categories TEXT[],                      -- Array of category names
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    is_premium BOOLEAN DEFAULT FALSE,
    price DECIMAL(10,2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admin_users(admin_id)
);

CREATE INDEX idx_design_templates_category ON design_templates(template_category);
CREATE INDEX idx_design_templates_active ON design_templates(is_active);


-- Option E: Add design reviews/moderation
-- (For admin approval of user designs before printing)
CREATE TABLE IF NOT EXISTS design_reviews (
    review_id SERIAL PRIMARY KEY,
    design_id INTEGER REFERENCES designs(design_id) ON DELETE CASCADE,
    order_item_id INTEGER REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    
    -- Review status
    status VARCHAR(20) DEFAULT 'pending',           -- pending, approved, rejected
    reviewed_by INTEGER REFERENCES admin_users(admin_id),
    reviewed_at TIMESTAMP,
    
    -- Review notes
    rejection_reason TEXT,
    admin_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (status IN ('pending', 'approved', 'rejected', 'needs_revision'))
);

CREATE INDEX idx_design_reviews_status ON design_reviews(status);
CREATE INDEX idx_design_reviews_design ON design_reviews(design_id);


-- ========================================
-- MIGRATION SCRIPT (if using Option C)
-- ========================================
-- Run this AFTER creating the designs table to migrate existing data

-- Migrate data from uploaded_files to designs
INSERT INTO designs (
    customer_id, 
    session_id, 
    design_url, 
    original_filename,
    created_at
)
SELECT 
    customer_id,
    session_id,
    file_url,
    original_filename,
    uploaded_at
FROM uploaded_files
WHERE file_url IS NOT NULL
AND (cart_item_id IS NOT NULL OR order_item_id IS NOT NULL);

-- Update cart_items to reference new designs
UPDATE cart_items ci
SET design_id = d.design_id
FROM designs d
WHERE ci.design_file_url = d.design_url;

-- Update order_items to reference new designs  
UPDATE order_items oi
SET design_id = d.design_id
FROM designs d
WHERE oi.design_file_url = d.design_url;



COMMIT;