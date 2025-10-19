#!/bin/bash

echo "=== Тестирование Shop API с PostgreSQL ==="
echo

echo "1. Создаем товары..."
curl -s -X POST http://localhost:8000/item \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 999.99}' | python3 -m json.tool
echo

curl -s -X POST http://localhost:8000/item \
  -H "Content-Type: application/json" \
  -d '{"name": "Mouse", "price": 29.99}' | python3 -m json.tool
echo

echo "2. Получаем список товаров..."
curl -s http://localhost:8000/item | python3 -m json.tool
echo

echo "3. Получаем товар по ID=1..."
curl -s http://localhost:8000/item/1 | python3 -m json.tool
echo

echo "4. Создаем корзину..."
CART_ID=$(curl -s -X POST http://localhost:8000/cart | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created cart ID: $CART_ID"
echo

echo "5. Добавляем товары в корзину..."
curl -s -X POST http://localhost:8000/cart/$CART_ID/add/1 | python3 -m json.tool
echo

curl -s -X POST http://localhost:8000/cart/$CART_ID/add/2 | python3 -m json.tool
echo

echo "6. Получаем корзину..."
curl -s http://localhost:8000/cart/$CART_ID | python3 -m json.tool
echo

echo "7. Обновляем товар (PUT)..."
curl -s -X PUT http://localhost:8000/item/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Gaming Laptop", "price": 1299.99}' | python3 -m json.tool
echo

echo "8. Частично обновляем товар (PATCH)..."
curl -s -X PATCH http://localhost:8000/item/2 \
  -H "Content-Type: application/json" \
  -d '{"price": 39.99}' | python3 -m json.tool
echo

echo "9. Удаляем товар..."
curl -s -X DELETE http://localhost:8000/item/2
echo "Deleted item 2"
echo

echo "10. Проверяем что товар помечен как удаленный..."
curl -s http://localhost:8000/item/2 2>&1 | head -1
echo

echo "=== Все тесты завершены! ==="
