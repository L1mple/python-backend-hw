CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    description TEXT,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE carts (
    id SERIAL PRIMARY KEY
);

CREATE TABLE cart_lines (
    cart_id INTEGER REFERENCES carts(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (cart_id, item_id)
);

CREATE INDEX idx_items_deleted ON items(deleted);
CREATE INDEX idx_items_name ON items(name);
CREATE INDEX idx_cart_lines_cart_id ON cart_lines(cart_id);
CREATE INDEX idx_cart_lines_item_id ON cart_lines(item_id);