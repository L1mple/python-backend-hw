-- Создание таблиц для магазина

DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS items CASCADE;

-- Таблица товаров
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица корзин
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    price DECIMAL(10, 2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица товаров в корзине
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Тестовые данные
INSERT INTO items (name, price) VALUES
    ('Laptop', 999.99),
    ('Mouse', 29.99),
    ('Keyboard', 79.99),
    ('Monitor', 299.99);

INSERT INTO carts (price) VALUES (0.0), (0.0);

INSERT INTO cart_items (cart_id, item_id, quantity) VALUES
    (1, 1, 1),
    (1, 2, 2),
    (2, 3, 1);
