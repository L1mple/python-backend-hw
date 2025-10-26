-- Очистка старых таблиц
DROP TABLE IF EXISTS items_in_carts CASCADE;
DROP TABLE IF EXISTS carts CASCADE;
DROP TABLE IF EXISTS items CASCADE;

-- Создание таблиц заново
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC(12,2) NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE carts (
    id SERIAL PRIMARY KEY
);

CREATE TABLE items_in_carts (
    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (cart_id, item_id)
);
