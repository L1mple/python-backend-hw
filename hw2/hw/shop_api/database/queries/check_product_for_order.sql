-- Проверка продукта перед созданием заказа
SELECT id, name, price, in_stock
FROM products
WHERE id = :product_id AND in_stock = TRUE;
