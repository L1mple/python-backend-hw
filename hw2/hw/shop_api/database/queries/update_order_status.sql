-- Обновление статуса заказа
UPDATE orders
SET status = :status
WHERE id = :order_id
RETURNING id, user_id, product_id, quantity, total_price, status, created_at;
