-- Получение всех заказов с информацией о пользователях и продуктах
SELECT 
    o.id,
    o.user_id,
    o.product_id,
    o.quantity,
    o.total_price,
    o.status,
    o.created_at,
    u.name as user_name,
    u.email as user_email,
    p.name as product_name,
    p.price as product_price
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN products p ON o.product_id = p.id
ORDER BY o.created_at DESC;
