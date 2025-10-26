-- Создание схемы базы данных для Shop API
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS items CASCADE;

-- Таблица товаров
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица корзин
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица связи корзин и товаров
CREATE TABLE cart_items (
    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (cart_id, item_id)
);

-- Индексы для оптимизации запросов
CREATE INDEX idx_items_deleted ON items(deleted);
CREATE INDEX idx_items_price ON items(price);
CREATE INDEX idx_cart_items_cart_id ON cart_items(cart_id);
CREATE INDEX idx_cart_items_item_id ON cart_items(item_id);

-- Вставка тестовых данных для проверки
INSERT INTO items (name, price, deleted) VALUES
    ('Туалетная бумага "Поцелуй", рулон', 50.00, FALSE),
    ('Золотая цепочка "Abendsonne"', 15000.00, FALSE),
    ('Молоко "Буреночка" 1л.', 159.99, FALSE),
    ('Хлеб белый', 45.50, FALSE),
    ('Удаленный товар', 100.00, TRUE);

