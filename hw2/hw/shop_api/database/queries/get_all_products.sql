-- Получение всех продуктов
SELECT id, name, price, description, in_stock, created_at
FROM products
ORDER BY created_at DESC;
