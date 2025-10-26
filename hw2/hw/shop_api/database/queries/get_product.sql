-- Получение продукта по ID
SELECT id, name, price, description, in_stock, created_at
FROM products
WHERE id = :product_id;
