"""Тестовый скрипт для проверки работы с корзинами"""
import asyncio
from database import AsyncSessionLocal
from data import item_queries, cart_queries
from data.models import ItemInfo, CartInfo, CartItemInfo


async def test_cart():
    """Тестирует операции с корзинами"""

    async with AsyncSessionLocal() as session:
        # 1. Создаем несколько товаров
        laptop = await item_queries.add(session, ItemInfo(name="Laptop", price=1500.0, deleted=False))
        mouse = await item_queries.add(session, ItemInfo(name="Mouse", price=50.0, deleted=False))
        keyboard = await item_queries.add(session, ItemInfo(name="Keyboard", price=100.0, deleted=False))
        await session.commit()
        print(f"✓ Созданы товары: Laptop (id={laptop.id}), Mouse (id={mouse.id}), Keyboard (id={keyboard.id})")

        # 2. Создаем пустую корзину
        empty_cart = await cart_queries.add(session, CartInfo(items=[], price=0.0))
        await session.commit()
        print(f"✓ Создана пустая корзина: {empty_cart}")

        # 3. Добавляем товары в корзину
        cart_with_laptop = await cart_queries.add_item_to_cart(session, empty_cart.id, laptop.id, quantity=1)
        await session.commit()
        print(f"✓ Добавлен laptop в корзину. Цена: {cart_with_laptop.info.price}")

        cart_with_mouse = await cart_queries.add_item_to_cart(session, empty_cart.id, mouse.id, quantity=2)
        await session.commit()
        print(f"✓ Добавлена мышь (2шт) в корзину. Цена: {cart_with_mouse.info.price}")

        # 4. Проверяем содержимое корзины
        cart = await cart_queries.get_one(session, empty_cart.id)
        print(f"\n✓ Корзина {cart.id}:")
        print(f"  Общая цена: ${cart.info.price}")
        print(f"  Товары:")
        for item in cart.info.items:
            print(f"    - {item.name} x{item.quantity} (доступен: {item.available})")

        # 5. Удаляем товар из корзины
        cart_without_mouse = await cart_queries.remove_item_from_cart(session, empty_cart.id, mouse.id)
        await session.commit()
        print(f"\n✓ Удалена мышь из корзины. Новая цена: {cart_without_mouse.info.price}")

        # 6. Помечаем товар как удаленный и проверяем available
        await item_queries.delete(session, laptop.id)
        await session.commit()

        cart_final = await cart_queries.get_one(session, empty_cart.id)
        print(f"\n✓ После удаления laptop из каталога:")
        for item in cart_final.info.items:
            print(f"    - {item.name}: доступен={item.available}")

        # 7. Создаем корзину с товарами сразу
        cart_items = [
            CartItemInfo(id=mouse.id, name=mouse.info.name, quantity=3, available=True),
            CartItemInfo(id=keyboard.id, name=keyboard.info.name, quantity=1, available=True)
        ]
        new_cart = await cart_queries.add(
            session,
            CartInfo(items=cart_items, price=0.0)
        )
        await session.commit()
        print(f"\n✓ Создана новая корзина с товарами:")
        print(f"  ID: {new_cart.id}")
        print(f"  Цена: ${new_cart.info.price}")
        print(f"  Товаров: {len(new_cart.info.items)}")

    print("\n✅ Все тесты корзины пройдены успешно!")


if __name__ == "__main__":
    asyncio.run(test_cart())
