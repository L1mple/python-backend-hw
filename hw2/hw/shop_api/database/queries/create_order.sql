-- Создание заказа с автоматическим вычислением стоимости
WITH product_info AS (
    SELECT price
    FROM products
    WHERE id = :product_id
)
INSERT INTO orders (user_id, product_id, quantity, total_price, status)
SELECT 
    :user_id,
    :product_id,
    :quantity,
    (SELECT price FROM product_info) * :quantity,
    'pending'
RETURNING id, user_id, product_id, quantity, total_price, status, created_at;
