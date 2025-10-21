
-- создание таблиц
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price FLOAT NOT NULL,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS carts (
    id SERIAL PRIMARY KEY,
    total_price INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INT REFERENCES carts(id) ON DELETE CASCADE,
    item_id INT REFERENCES items(id) ON DELETE CASCADE,
    quantity INT DEFAULT 1
);

-- Вставка тестовых данных
INSERT INTO items (name, price) VALUES
('Laptop', 12.5),
('Headphones', 15.8),
('Mouse', 25.3);

INSERT INTO carts(total_price) VALUES
(200),
(300),
(100);

INSERT INTO cart_items(cart_id, item_id, quantity) VALUES
(1, 1, 200),
(2, 2, 400),
(3, 3, 900);

