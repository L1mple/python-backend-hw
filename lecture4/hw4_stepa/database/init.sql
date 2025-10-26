CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    cost DECIMAL(10, 2) NOT NULL CHECK (cost >= 0),
    is_removed BOOLEAN DEFAULT FALSE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS baskets (
    id SERIAL PRIMARY KEY,
    total_cost DECIMAL(10, 2) DEFAULT 0.0,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS basket_products (
    id SERIAL PRIMARY KEY,
    basket_id INTEGER NOT NULL REFERENCES baskets(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    amount INTEGER DEFAULT 1 CHECK (amount > 0),
    is_active BOOLEAN DEFAULT TRUE,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial test data
INSERT INTO products (title, cost) VALUES
    ('MacBook Pro', 1999.99),
    ('AirPods', 179.99),
    ('Magic Mouse', 79.99),
    ('Thunderbolt Display', 1299.99);

INSERT INTO baskets (total_cost) VALUES (0.0), (0.0);

INSERT INTO basket_products (basket_id, product_id, amount) VALUES
    (1, 1, 1),
    (1, 2, 1),
    (2, 3, 2);
