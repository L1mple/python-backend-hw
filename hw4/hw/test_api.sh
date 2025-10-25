#!/bin/bash
echo "🚀 ТЕСТИРОВАНИЕ SHOP API с SQLAlchemy"

BASE_URL="http://localhost:8080"

echo "1. Создаем товары..."
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Laptop", "price": 999.99}'
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Mouse", "price": 29.99}'
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Keyboard", "price": 79.99}'

echo -e "\n2. Все товары:"
curl "$BASE_URL/item"

echo -e "\n3. Создаем корзину..."
CART_ID=$(curl -s -X POST "$BASE_URL/cart" | jq -r '.id')
echo "Корзина ID: $CART_ID"

echo -e "\n4. Добавляем товары в корзину..."
curl -X POST "$BASE_URL/cart/$CART_ID/add/1"
curl -X POST "$BASE_URL/cart/$CART_ID/add/2"
curl -X POST "$BASE_URL/cart/$CART_ID/add/1"

echo -e "\n5. Корзина:"
curl "$BASE_URL/cart/$CART_ID"

echo -e "\n6. Обновляем товар..."
curl -X PUT "$BASE_URL/item/1?name=Laptop%20Pro&price=1299.99"

echo -e "\n7. Частичный апдейт..."
curl -X PATCH "$BASE_URL/item/2" -H "Content-Type: application/json" -d '{"name": "Wireless Mouse"}'

echo -e "\n8. Корзина после обновления:"
curl "$BASE_URL/cart/$CART_ID"

echo -e "\n9. Удаляем товар (soft delete)..."
curl -X DELETE "$BASE_URL/item/3"

echo -e "\n10. Фильтрация товаров (цена 50-1000):"
curl "$BASE_URL/item?min_price=50&max_price=1000"

echo -e "\n11. Все корзины:"
curl "$BASE_URL/cart"

echo "Все тесты выполнены!"