-- Создание продукта
INSERT INTO products (name, price, description, in_stock)
VALUES (:name, :price, :description, :in_stock)
RETURNING id, name, price, description, in_stock, created_at;
