# Проверка товара для заказа
SELECT Product {
    id,
    name,
    in_stock
}
FILTER .id = <uuid>$product_id
