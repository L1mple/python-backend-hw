#!/bin/bash

echo "🚀 ТЕСТИРОВАНИЕ SHOP API с SQLAlchemy"

BASE_URL="http://localhost:8000"

echo "1. Проверяем здоровье API..."
curl -s "$BASE_URL/"

echo -e "\n\n2. Создаем новые товары..."
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Gaming Laptop", "price": 1499.99}'
echo ""
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Wireless Mouse", "price": 49.99}'
echo ""
curl -X POST "$BASE_URL/item" -H "Content-Type: application/json" -d '{"name": "Mechanical Keyboard", "price": 129.99}'

echo -e "\n3. Получаем все товары:"
curl -s "$BASE_URL/item" | python3 -m json.tool

echo -e "\n4. Создаем корзину..."
CART_RESPONSE=$(curl -s -X POST "$BASE_URL/cart")
echo "$CART_RESPONSE"
CART_ID=$(echo "$CART_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Корзина ID: $CART_ID"

echo -e "\n5. Добавляем товары в корзину..."
curl -X POST "$BASE_URL/cart/$CART_ID/add/5"  # Gaming Laptop
echo ""
curl -X POST "$BASE_URL/cart/$CART_ID/add/6"  # Wireless Mouse
echo ""
curl -X POST "$BASE_URL/cart/$CART_ID/add/5"  # Еще один Gaming Laptop

echo -e "\n6. Показываем корзину:"
curl -s "$BASE_URL/cart/$CART_ID" | python3 -m json.tool

echo -e "\n7. Обновляем товар (полная замена)..."
curl -X PUT "$BASE_URL/item/6" -H "Content-Type: application/json" -d '{"name": "Premium Wireless Mouse", "price": 79.99}'
echo ""

echo -e "\n8. Частичное обновление товара..."
curl -X PATCH "$BASE_URL/item/7" -H "Content-Type: application/json" -d '{"price": 149.99}'
echo ""

echo -e "\n9. Корзина после обновления цен:"
curl -s "$BASE_URL/cart/$CART_ID" | python3 -m json.tool

echo -e "\n10. Удаляем товар (soft delete)..."
curl -X DELETE "$BASE_URL/item/3"  # Keyboard
echo ""

echo -e "\n11. Фильтрация товаров (цена 50-1000):"
curl -s "$BASE_URL/item?min_price=50&max_price=1000" | python3 -m json.tool

echo -e "\n12. Все корзины:"
curl -s "$BASE_URL/cart" | python3 -m json.tool

echo -e "\n13. Тестируем уровни изоляции..."
echo "Матрица изоляции:"
curl -s "$BASE_URL/item/isolation/matrix" | python3 -m json.tool

echo -e "\nDirty Read тест:"
curl -s "$BASE_URL/item/isolation/dirty/1" | python3 -m json.tool

echo -e "\nNon-repeatable Read тест:"
curl -s "$BASE_URL/item/isolation/non_repeatable/1" | python3 -m json.tool

echo -e "\nPhantom Read тест:"
curl -s "$BASE_URL/item/isolation/phantom/100" | python3 -m json.tool

echo -e "\n✅ Все тесты выполнены!"
