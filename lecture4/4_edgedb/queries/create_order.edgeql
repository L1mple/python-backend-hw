# Создание заказа с автоматическим вычислением стоимости
WITH
    user := (SELECT User FILTER .id = <uuid>$user_id),
    product := (SELECT Product FILTER .id = <uuid>$product_id)
INSERT Order {
    user := user,
    product := product,
    quantity := <int32>$quantity,
    total_price := product.price * <decimal><int32>$quantity,
    status := 'pending'
}
