
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