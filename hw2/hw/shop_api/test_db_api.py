#!/usr/bin/env python3
import asyncio
import httpx
import os
from decimal import Decimal

BASE_URL = "http://localhost:8080"

async def test_database_api():
    async with httpx.AsyncClient() as client:

        print("\n1. Создание пользователя...")
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "age": 25
        }
        response = await client.post(f"{BASE_URL}/users/", json=user_data)
        print(f"   POST /users/ - Status: {response.status_code}")
        if response.status_code == 201:
            user = response.json()
            user_id = user["id"]
            print(f"Создан пользователь ID: {user_id}")
        else:
            print(f"   Ошибка: {response.text}")
            return

        print("\n2. Создание продуктов...")
        products_data = [
            {"name": "Laptop", "price": 999.99, "description": "Gaming laptop"},
            {"name": "Mouse", "price": 29.99, "description": "Wireless mouse"},
            {"name": "Keyboard", "price": 79.99, "description": "Mechanical keyboard"}
        ]

        product_ids = []
        for product_data in products_data:
            response = await client.post(f"{BASE_URL}/products/", json=product_data)
            print(f"   POST /products/ - Status: {response.status_code}")
            if response.status_code == 201:
                product = response.json()
                product_ids.append(product["id"])
                print(f"Создан продукт: {product['name']} (ID: {product['id']})")
            else:
                print(f"   Ошибка: {response.text}")

        print("\n3. Тестирование API предметов...")
        response = await client.get(f"{BASE_URL}/item/")
        print(f"   GET /item/ - Status: {response.status_code}")
        if response.status_code == 200:
            items = response.json()
            print(f"   Найдено {len(items)} предметов")

        print("\n4. Создание корзины...")
        cart_data = {
            "email": "cart@example.com",
            "name": "Shopping Cart",
            "age": 18
        }
        response = await client.post(f"{BASE_URL}/users/", json=cart_data)
        print(f"   POST /users/ (cart) - Status: {response.status_code}")
        if response.status_code == 201:
            cart = response.json()
            cart_id = cart["id"]
            print(f"   Создана корзина ID: {cart_id}")

            print("\n5. Добавление предметов в корзину...")
            for product_id in product_ids[:2]:
                response = await client.post(f"{BASE_URL}/cart/{cart_id}/add/{product_id}")
                print(f"   POST /cart/{cart_id}/add/{product_id} - Status: {response.status_code}")
                if response.status_code == 200:
                    cart_response = response.json()
                    print(f"   Корзина обновлена: {len(cart_response['items'])} items, price: {cart_response['price']}")

        print("\n6. Создание заказа...")
        order_data = {
            "user_id": cart_id,
            "product_id": product_ids[0],
            "quantity": 2,
            "status": "pending"
        }
        response = await client.post(f"{BASE_URL}/orders/", json=order_data)
        print(f"   POST /orders/ - Status: {response.status_code}")
        if response.status_code == 201:
            order = response.json()
            print(f"   Создан заказ ID: {order['id']}, total: {order['total_price']}")

        print("\n7. Получение заказов...")
        response = await client.get(f"{BASE_URL}/orders/")
        print(f"   GET /orders/ - Status: {response.status_code}")
        if response.status_code == 200:
            orders = response.json()
            print(f"   Найдено {len(orders)} заказов")

async def test_health():
    async with httpx.AsyncClient() as client:
        print("🔍 Endpoints...")

        response = await client.get(f"{BASE_URL}/metrics")
        print(f"   GET /metrics - Status: {response.status_code}")

        response = await client.get(f"{BASE_URL}/docs")
        print(f"   GET /docs - Status: {response.status_code}")

        print("Endpoints тесты завершены!")

async def main():
    print("API...")

    await asyncio.sleep(2)

    try:
        await test_health()
        await test_database_api()
        print("\n Все тесты завершены!")
    except Exception as e:
        print(f"\n Тесты не прошли: {e}")

if __name__ == "__main__":
    asyncio.run(main())
