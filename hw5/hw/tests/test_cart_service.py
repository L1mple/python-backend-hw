import pytest
from hw5.hw.shop_api.store.services import CartService, ItemService
from hw5.hw.shop_api.store.models import CartResponse, CartItemResponse


class TestCartService:
    def test_create_cart(self, session):
        service = CartService(session)
        cart_id = service.create_cart()["id"]
        assert isinstance(cart_id, int)

    def test_add_item_to_cart(self, session, create_test_items):
        service = CartService(session)
        cart_id = service.create_cart()["id"]
        service.add_item_to_cart(cart_id, create_test_items[0])

        cart = service.get_cart(cart_id)
        assert len(cart.items) == 1
        assert cart.items[0].available is True

    def test_get_cart_with_deleted_item(self, session, create_test_items):
        service = CartService(session)
        cart_id = service.create_cart()["id"]
        service.add_item_to_cart(cart_id, create_test_items[0])

        # Удаляем товар
        item_service = ItemService(session)
        item_service.delete_item(create_test_items[0])

        cart = service.get_cart(cart_id)
        assert len(cart.items) == 1
        assert cart.items[0].available is False
        assert cart.price == 0.0

    def test_cart_price_recalculation(self, session, create_test_items):
        service = CartService(session)
        cart_id = service.create_cart()["id"]
        service.add_item_to_cart(cart_id, create_test_items[0])
        service.add_item_to_cart(cart_id, create_test_items[1])

        cart = service.get_cart(cart_id)
        assert abs(cart.price - 129.98) < 0.01

    def test_add_same_item_multiple_times(self, session, create_test_items):
        service = CartService(session)
        cart_id = service.create_cart()["id"]
        service.add_item_to_cart(cart_id, create_test_items[0])
        service.add_item_to_cart(cart_id, create_test_items[0])

        cart = service.get_cart(cart_id)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 2

        def test_get_carts_edge_cases(self, session, create_test_carts_with_items):
            service = CartService(session)

            # Тест с различными комбинациями фильтров
            carts = service.get_carts(min_price=50.0)
            assert isinstance(carts, list)

            carts = service.get_carts(max_price=100.0)
            assert isinstance(carts, list)

            carts = service.get_carts(min_quantity=1)
            assert isinstance(carts, list)

            carts = service.get_carts(max_quantity=10)
            assert isinstance(carts, list)

            # Тест со всеми фильтрами одновременно
            carts = service.get_carts(
                min_price=10.0,
                max_price=200.0,
                min_quantity=1,
                max_quantity=5
            )
            assert isinstance(carts, list)

            # Тест когда нет подходящих корзин
            carts = service.get_carts(min_price=100000.0)
            assert carts == []

            # Тест с offset превышающим количество корзин
            carts = service.get_carts(offset=1000, limit=10)
            assert carts == []

            # Тест с очень большим limit
            carts = service.get_carts(offset=0, limit=1000)
            assert len(carts) <= 1000

        def test_add_item_edge_cases(self, session, create_test_items):
            service = CartService(session)
            item_service = ItemService(session)

            # Тест добавления в несуществующую корзину
            with pytest.raises(HTTPException) as exc:
                service.add_item_to_cart(999999, create_test_items[0])
            assert exc.value.status_code == 404

            # Тест добавления несуществующего товара
            cart_id = service.create_cart()["id"]
            with pytest.raises(HTTPException) as exc:
                service.add_item_to_cart(cart_id, 999999)
            assert exc.value.status_code == 404

            # Тест добавления удаленного товара
            item_id = create_test_items[0]
            item_service.delete_item(item_id)
            with pytest.raises(HTTPException) as exc:
                service.add_item_to_cart(cart_id, item_id)
            assert exc.value.status_code == 404

        def test_cart_price_calculation_edge_cases(self, session, create_test_items):
            service = CartService(session)

            # Тест пустой корзины
            cart_id = service.create_cart()["id"]
            cart = service.get_cart(cart_id)
            assert cart.price == 0.0
            assert cart.items == []

            # Тест корзины с товаром с нулевой ценой
            item_service = ItemService(session)
            zero_price_item = item_service.create_item(ItemCreate(name="Free Item", price=0.0))

            service.add_item_to_cart(cart_id, zero_price_item.id)
            cart = service.get_cart(cart_id)
            assert cart.price == 0.0

            # Тест корзины с большим количеством товаров
            for i in range(5):
                service.add_item_to_cart(cart_id, create_test_items[i % len(create_test_items)])

            cart = service.get_cart(cart_id)
            assert cart.price > 0.0

        def test_quantity_edge_cases(self, session, create_test_items):
            service = CartService(session)
            cart_id = service.create_cart()["id"]

            # Добавляем один товар много раз
            for i in range(10):
                service.add_item_to_cart(cart_id, create_test_items[0])

            cart = service.get_cart(cart_id)
            item = next((item for item in cart.items if item.name == "Bread"), None)
            assert item.quantity == 10

