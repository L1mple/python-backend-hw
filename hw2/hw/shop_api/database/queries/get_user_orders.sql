-- Получение всех заказов пользователя
SELECT 
    o.id,
    o.user_id,
    o.product_id,
    o.quantity,
    o.total_price,
    o.status,
    o.created_at,
    p.name as product_name,
    p.price as product_price
FROM orders o
JOIN products p ON o.product_id = p.id
WHERE o.user_id = :user_id
ORDER BY o.created_at DESC;
