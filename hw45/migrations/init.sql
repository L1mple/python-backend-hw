-- Создание схемы базы данных для примеров
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;

-- Таблица корзин
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
);

-- Таблица продуктов
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    deleted BOOLEAN DEFAULT FALSE,
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
);

-- -- Вставка тестовых данных
-- INSERT INTO users (email, name, age) VALUES
--     ('alice@example.com', 'Alice Johnson', 28),
--     ('bob@example.com', 'Bob Smith', 35),
--     ('charlie@example.com', 'Charlie Brown', 42);

-- INSERT INTO products (name, price, description, in_stock) VALUES
--     ('Laptop', 999.99, 'High-performance laptop', TRUE),
--     ('Mouse', 29.99, 'Wireless optical mouse', TRUE),
--     ('Keyboard', 79.99, 'Mechanical gaming keyboard', FALSE),
--     ('Monitor', 299.99, '24-inch LCD monitor', TRUE);

-- INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES
--     (1, 1, 1, 999.99, 'delivered'),
--     (1, 2, 2, 59.98, 'shipped'),
--     (2, 3, 1, 79.99, 'processing'),
--     (3, 4, 1, 299.99, 'pending');
