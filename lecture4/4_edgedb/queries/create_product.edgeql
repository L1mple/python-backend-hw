# Создание продукта
INSERT Product {
    name := <str>$name,
    price := <decimal>$price,
    description := <optional str>$description,
    in_stock := <bool>$in_stock
}
