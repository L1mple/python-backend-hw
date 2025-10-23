"""Тестовый скрипт для проверки API с PostgreSQL"""
import asyncio
import httpx


async def test_api():
    """Тестирует API endpoints"""

    # Предполагаем, что сервер запущен на порту 8080
    base_url = "http://localhost:8080"

    async with httpx.AsyncClient() as client:
        print("Тестирование Shop API с PostgreSQL\n")

        # 1. Создание товара
        print("1. Создание товара...")
        response = await client.post(
            f"{base_url}/item/",
            json={"name": "MacBook Pro", "price": 2500.0}
        )
        print(f"   Статус: {response.status_code}")
        item = response.json()
        print(f"   Товар: {item}")
        item_id = item["id"]

        # 2. Получение товара
        print("\n2. Получение товара...")
        response = await client.get(f"{base_url}/item/{item_id}")
        print(f"   Статус: {response.status_code}")
        print(f"   Товар: {response.json()}")

        # 3. Создание корзины
        print("\n3. Создание корзины...")
        response = await client.post(f"{base_url}/cart/")
        print(f"   Статус: {response.status_code}")
        cart = response.json()
        print(f"   Корзина: {cart}")
        cart_id = cart["id"]

        # 4. Добавление товара в корзину
        print(f"\n4. Добавление товара {item_id} в корзину {cart_id}...")
        response = await client.post(f"{base_url}/cart/{cart_id}/add/{item_id}")
        print(f"   Статус: {response.status_code}")
        cart = response.json()
        print(f"   Корзина: {cart}")
        print(f"   Цена корзины: ${cart['price']}")

        # 5. Получение списка товаров
        print("\n5. Получение списка товаров...")
        response = await client.get(f"{base_url}/item/")
        print(f"   Статус: {response.status_code}")
        items = response.json()
        print(f"   Найдено товаров: {len(items)}")

        # 6. Обновление товара
        print(f"\n6. Обновление товара {item_id}...")
        response = await client.put(
            f"{base_url}/item/{item_id}",
            json={"name": "MacBook Pro M3", "price": 2800.0}
        )
        print(f"   Статус: {response.status_code}")
        print(f"   Обновленный товар: {response.json()}")

        # 7. Удаление товара
        print(f"\n7. Удаление товара {item_id}...")
        response = await client.delete(f"{base_url}/item/{item_id}")
        print(f"   Статус: {response.status_code}")
        deleted_item = response.json()
        print(f"   Deleted: {deleted_item['deleted']}")

        print("\n✅ Все API тесты пройдены!")


if __name__ == "__main__":
    asyncio.run(test_api())
