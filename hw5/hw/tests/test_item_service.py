import pytest
from hw5.hw.shop_api.store.services import ItemService
from hw5.hw.shop_api.store.models import ItemCreate, ItemResponse
from hw5.hw.shop_api.db.database import ItemDB
from fastapi import HTTPException
from hw5.hw.shop_api.db.settings import DATABASE_URL

class TestItemService:
    def test_create_item(self, session, create_test_items):
        service = ItemService(session)
        item = service.create_item(ItemCreate(name="Test Item", price=123.45))
        assert item.name == "Test Item"
        assert item.price == 123.45
        assert item.deleted is False

    def test_get_item_success(self, session, create_test_items):
        service = ItemService(session)
        item = service.get_item(create_test_items[0])
        assert item.__class__.__name__ == "ItemResponse"


    def test_get_item_not_found(self, session):
        service = ItemService(session)
        with pytest.raises(HTTPException) as exc:
            service.get_item(999)
        assert exc.value.status_code == 404

    def test_get_items_filtering(self, session, create_test_items):
        service = ItemService(session)
        items = service.get_items(min_price=50, max_price=100, show_deleted=False)
        assert len(items) >= 2

    def test_replace_item(self, session, create_test_items):
        service = ItemService(session)
        updated = service.replace_item(
            create_test_items[0],
            ItemCreate(name="Bread new", price=69.99)
        )
        assert updated.name == "Bread new"
        assert updated.price == 69.99

    def test_update_item_partial(self, session, create_test_items):
        service = ItemService(session)
        result = service.update_item(
            create_test_items[0],
            {"name": "Partial Update"}
        )
        assert result.name == "Partial Update"

    def test_update_deleted_item(self, session, create_test_items):
        service = ItemService(session)
        # Удаляем товар
        service.delete_item(create_test_items[0])
        with pytest.raises(HTTPException) as exc:
            service.update_item(create_test_items[0], {"price": 100})
        assert exc.value.status_code == 304

    def test_delete_item_soft(self, session, create_test_items):
        service = ItemService(session)
        service.delete_item(create_test_items[0])
        item = session.get(ItemDB, create_test_items[0])
        assert item.deleted is True

    def test_create_item_edge_cases(self, session):
        """Крайние случаи для создания товара"""
        service = ItemService(session)

        # Тест с минимальной ценой
        item = service.create_item(ItemCreate(name="Min Price", price=0.01))
        assert item.price == 0.01

        long_name = "A" * 100
        item = service.create_item(ItemCreate(name=long_name, price=10.0))
        assert item.name == long_name

    def test_get_items_edge_cases(self, session, create_test_items):
        service = ItemService(session)

        # Тест с offset превышающим количество товаров
        items = service.get_items(offset=1000, limit=10)
        assert items == []

        # Тест с очень большим limit
        items = service.get_items(offset=0, limit=1000)
        assert len(items) <= 1000

        # Тест с одинаковыми min_price и max_price
        items = service.get_items(min_price=50.0, max_price=50.0)
        for item in items:
            assert item.price == 50.0

        # Тест с show_deleted=True
        item_id = create_test_items[0]
        service.delete_item(item_id)
        items_with_deleted = service.get_items(show_deleted=True)
        deleted_items = [item for item in items_with_deleted if item.deleted]
        assert len(deleted_items) >= 1

    def test_update_item_edge_cases(self, session, create_test_items):
        service = ItemService(session)
        item_id = create_test_items[0]

        # Тест обновления несуществующего товара
        result = service.update_item(999999, {"name": "Test"})
        assert result is None

        # Тест с пустыми обновлениями
        result = service.update_item(item_id, {})
        assert result is not None

        # Тест с невалидными полями
        result = service.update_item(item_id, {"invalid_field": "value"})
        assert result is not None

        # Тест обновления только цены
        result = service.update_item(item_id, {"price": 999.99})
        assert result.price == 999.99

        # Тест обновления только названия
        result = service.update_item(item_id, {"name": "Updated Name"})
        assert result.name == "Updated Name"

    def test_delete_item_edge_cases(self, session):
        service = ItemService(session)

        # Тест удаления несуществующего товара
        service.delete_item(999999)

        # Тест повторного удаления товара
        item = service.create_item(ItemCreate(name="Temp Item", price=10.0))
        service.delete_item(item.id)
        service.delete_item(item.id)
        db_item = session.get(ItemDB, item.id)
        assert db_item.deleted is True