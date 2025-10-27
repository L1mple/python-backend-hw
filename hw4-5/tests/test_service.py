import sys, os
import pytest
from unittest.mock import Mock, MagicMock
from http import HTTPStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from service.main import (
    app,
    Item, Cart, ItemInCart,
    ItemMapper, CartMapper, ItemInCartMapper,
    SqlAlchemyItemRepository, SqlAlchemyCartRepository,
    ItemOrm, CartOrm, ItemInCartOrm, Base
)

class TestItemRepository:
    @pytest.fixture
    def mock_session(self):
        session = Mock(spec=Session)
        session.query.return_value.filter_by.return_value.first.return_value = None
        return session
    
    @pytest.fixture
    def item_repo(self, mock_session):
        return SqlAlchemyItemRepository(mock_session)
    
    def test_delete_item_in_carts(self, item_repo, mock_session, mocker):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.price = 100.0
        orm_item.deleted = False

        orm_cart_item = MagicMock(spec=ItemInCartOrm)
        orm_cart_item.item_id = 1
        orm_cart_item.cart_id = 1
        orm_cart_item.quantity = 2
        orm_cart_item.available = True
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 200.0  # 2 * 100.0

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [orm_item, orm_cart]
        mock_session.query.return_value.filter_by.return_value.all.return_value = [orm_cart_item]

        mock_session.flush = Mock()

        item_repo.delete(item_id=1)

        assert orm_item.deleted is True
        assert orm_cart_item.available is False
        assert orm_cart.price == 0.0
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.query.return_value.filter_by.assert_any_call(item_id=1)
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.flush.assert_called_once()

    def test_create_item(self, item_repo, mock_session, mocker):
        item = Item(name="Apple", price=150.0)
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = None
        orm_item.name = "Apple"
        orm_item.price = 150.0

        mocker.patch('service.main.ItemMapper.to_orm', return_value=orm_item)
        def flush_side_effect():
            orm_item.configure_mock(id=1)
            return None
        mock_session.add.return_value = None
        mock_session.flush.side_effect = flush_side_effect
       
        result = item_repo.create(item)

        assert result.id == 1
        assert result.name == "Apple"
        assert result.price == 150.0
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_find_by_id_found(self, item_repo, mock_session):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False
        mock_session.query.return_value.filter_by.return_value.first.return_value = orm_item

        result = item_repo.find_by_id(1)

        assert result.id == 1
        assert result.name == "Apple"
        assert result.price == 150.0
        assert result.deleted == False
        mock_session.query.return_value.filter_by.assert_called_once_with(id=1)

    def test_get_all(self, item_repo, mock_session, mocker):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False

        mock_query = Mock()
        mock_session.query.return_value = mock_query

        mock_filter_by = Mock()
        mock_query.filter_by.return_value = mock_filter_by

        mock_filter_min = Mock()
        mock_filter_by.filter.return_value = mock_filter_min
        mock_filter_max = Mock()
        mock_filter_min.filter.return_value = mock_filter_max

        mock_offset = Mock()
        mock_filter_max.offset.return_value = mock_offset
        mock_limit = Mock()
        mock_offset.limit.return_value = mock_limit

        mock_limit.all.return_value = [orm_item]

        mocker.patch('service.main.ItemMapper.to_domain', return_value=Item(id=1, name="Apple", price=150.0, deleted=False))

        result = item_repo.get_all(offset=0, limit=10, min_price=100.0, max_price=200.0, show_deleted=False)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Apple"
        assert result[0].price == 150.0
        assert result[0].deleted == False
        mock_query.filter_by.assert_called_once_with(deleted=False)
        mock_filter_by.filter.assert_called_once()
        mock_filter_min.filter.assert_called_once()
        mock_filter_max.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(10)
        mock_limit.all.assert_called_once()


    def test_update_success(self, item_repo, mock_session, mocker):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False
        mock_session.query.return_value.filter_by.return_value.first.return_value = orm_item
        mock_session.query.return_value.filter_by.return_value.all.return_value = []  # Пустой список для ItemInCartOrm
        mocker.patch('service.main.ItemMapper.to_orm', return_value=orm_item)
        
        def flush_side_effect():
            orm_item.configure_mock(name="Updated Apple", price=200.0)
            return None
        
        mock_session.flush.side_effect = flush_side_effect

        item = Item(id=1, name="Updated Apple", price=200.0, deleted=False)
        result = item_repo.update(item)

        assert result.id == 1
        assert result.name == "Updated Apple"
        assert result.price == 200.0
        assert result.deleted == False
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.flush.assert_called_once()

    def test_update_not_found(self, item_repo, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        item = Item(id=1, name="Apple", price=150.0, deleted=False)
        with pytest.raises(ValueError, match="Item with id 1 not found"):
            item_repo.update(item)

        mock_session.query.return_value.filter_by.assert_called_once_with(id=1)

    def test_delete_success(self, item_repo, mock_session):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False
        mock_session.query.return_value.filter_by.return_value.first.return_value = orm_item
        mock_session.query.return_value.filter_by.return_value.all.return_value = []  # Пустой список для ItemInCartOrm
        
        def flush_side_effect():
            orm_item.configure_mock(deleted=True)
            return None
        
        mock_session.flush.side_effect = flush_side_effect

        item_repo.delete(1)

        assert orm_item.deleted is True
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.flush.assert_called_once()

    def test_delete_not_found(self, item_repo, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Item with id 1 not found"):
            item_repo.delete(1)

        mock_session.query.return_value.filter_by.assert_called_once_with(id=1)


    def test_update_with_cart_items(self, item_repo, mock_session, mocker):
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False

        orm_cart_item = MagicMock(spec=ItemInCartOrm)
        orm_cart_item.cart_id = 1
        orm_cart_item.quantity = 2
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 300.0

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [orm_item, orm_cart]
        mock_session.query.return_value.filter_by.return_value.all.return_value = [orm_cart_item]

        mocker.patch('service.main.ItemMapper.to_orm', return_value=orm_item)
        mocker.patch('service.main.ItemMapper.to_domain', return_value=Item(id=1, name="Updated Apple", price=200.0, deleted=False))

        def flush_side_effect():
            orm_item.configure_mock(name="Updated Apple", price=200.0)
            orm_cart.configure_mock(price=400.0)
            return None
        mock_session.flush.side_effect = flush_side_effect

        item = Item(id=1, name="Updated Apple", price=200.0, deleted=False)
        result = item_repo.update(item)

        assert result.id == 1
        assert result.name == "Updated Apple"
        assert result.price == 200.0
        assert result.deleted is False
        assert orm_cart.price == 400.0
        mock_session.flush.assert_called_once()

class TestCartRepository:
    @pytest.fixture
    def mock_session(self):
        session = Mock(spec=Session)
        session.query.return_value.filter_by.return_value.first.return_value = None
        return session

    @pytest.fixture
    def cart_repo(self, mock_session):
        return SqlAlchemyCartRepository(mock_session)

    def test_create_cart(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = None
        orm_cart.price = 0.0
        orm_cart.items = []

        mocker.patch('service.main.CartOrm', return_value=orm_cart)
        def flush_side_effect():
            orm_cart.configure_mock(id=1)
            return None
        mock_session.add.return_value = None
        mock_session.flush.side_effect = flush_side_effect

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[], price=0.0))

        result = cart_repo.create()

        assert result.id == 1
        assert result.price == 0.0
        assert result.items == []
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_find_by_id_found(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 0.0
        orm_cart.items = []
        mock_session.query.return_value.filter_by.return_value.first.return_value = orm_cart

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[], price=0.0))

        result = cart_repo.find_by_id(1)

        assert result.id == 1
        assert result.price == 0.0
        assert result.items == []
        mock_session.query.return_value.filter_by.assert_called_once_with(id=1)

    def test_get_all(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 100.0
        orm_cart.items = []

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter_min = Mock()
        mock_query.filter.return_value = mock_filter_min
        mock_filter_max = Mock()
        mock_filter_min.filter.return_value = mock_filter_max
        mock_offset = Mock()
        mock_filter_max.offset.return_value = mock_offset
        mock_limit = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = [orm_cart]

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[], price=100.0))

        result = cart_repo.get_all(offset=0, limit=10, min_price=50.0, max_price=150.0, min_quantity=None, max_quantity=None)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].price == 100.0
        assert result[0].items == []
        mock_query.filter.assert_called_once()
        mock_filter_min.filter.assert_called_once()
        mock_filter_max.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(10)
        mock_limit.all.assert_called_once()

    def test_add_item_new_item(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 0.0
        orm_cart.items = []
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [orm_cart, orm_item]

        orm_cart_item = MagicMock(spec=ItemInCartOrm)
        mocker.patch('service.main.ItemInCartOrm', return_value=orm_cart_item)

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[ItemInCart(id=None, item_id=1, name="Apple", quantity=1, available=True)], price=150.0))

        def flush_side_effect():
            orm_cart.configure_mock(price=150.0)
            orm_cart_item.configure_mock(id=1)
            return None
        mock_session.flush.side_effect = flush_side_effect

        result = cart_repo.add_item(cart_id=1, item_id=1)

        assert result.id == 1
        assert result.price == 150.0
        assert len(result.items) == 1
        assert result.items[0].item_id == 1
        assert result.items[0].name == "Apple"
        assert result.items[0].quantity == 1
        assert result.items[0].available is True
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.flush.assert_called_once()

    def test_add_item_existing_item(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 150.0
        orm_cart_item = MagicMock(spec=ItemInCartOrm)
        orm_cart_item.item_id = 1
        orm_cart_item.quantity = 1
        orm_cart.items = [orm_cart_item]
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [orm_cart, orm_item]

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[ItemInCart(id=None, item_id=1, name="Apple", quantity=2, available=True)], price=300.0))

        def flush_side_effect():
            orm_cart.configure_mock(price=300.0)
            orm_cart_item.configure_mock(quantity=2)
            return None
        mock_session.flush.side_effect = flush_side_effect

        result = cart_repo.add_item(cart_id=1, item_id=1)

        assert result.id == 1
        assert result.price == 300.0
        assert len(result.items) == 1
        assert result.items[0].item_id == 1
        assert result.items[0].name == "Apple"
        assert result.items[0].quantity == 2
        assert result.items[0].available is True
        mock_session.query.return_value.filter_by.assert_any_call(id=1)
        mock_session.flush.assert_called_once()

    def test_add_item_cart_not_found(self, cart_repo, mock_session):
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Cart with id 1 not found"):
            cart_repo.add_item(cart_id=1, item_id=1)

        mock_session.query.return_value.filter_by.assert_called_once_with(id=1)

    def test_add_item_item_not_found(self, cart_repo, mock_session):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 0.0
        orm_cart.items = []

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [orm_cart, None]

        with pytest.raises(ValueError, match="Item with id 1 not found"):
            cart_repo.add_item(cart_id=1, item_id=1)

        mock_session.query.return_value.filter_by.assert_any_call(id=1)

    def test_get_all_with_quantity_filters(self, cart_repo, mock_session, mocker):
        orm_cart = MagicMock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 100.0
        orm_cart.items = []

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_join = Mock()
        mock_query.join.return_value = mock_join
        mock_group_by = Mock()
        mock_join.group_by.return_value = mock_group_by
        mock_having_min = Mock()
        mock_group_by.having.return_value = mock_having_min
        mock_having_max = Mock()
        mock_having_min.having.return_value = mock_having_max
        mock_offset = Mock()
        mock_having_max.offset.return_value = mock_offset
        mock_limit = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = [orm_cart]

        mocker.patch('service.main.CartMapper.to_domain', return_value=Cart(id=1, items=[], price=100.0))

        result = cart_repo.get_all(offset=0, limit=10, min_price=None, max_price=None, min_quantity=1, max_quantity=5)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].price == 100.0
        assert result[0].items == []
        mock_query.join.assert_called_once_with(ItemInCartOrm)
        mock_join.group_by.assert_called_once_with(CartOrm.id)
        mock_group_by.having.assert_called_once()
        mock_having_min.having.assert_called_once()
        mock_having_max.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(10)
        mock_limit.all.assert_called_once()


class TestMappers:
    def test_item_mapper_to_orm_new(self):
        domain_item = Item(id=None, name="Apple", price=150.0, deleted=False)

        result = ItemMapper.to_orm(domain_item)

        assert isinstance(result, ItemOrm)
        assert result.id is None
        assert result.name == "Apple"
        assert result.price == 150.0
        assert result.deleted is False

    def test_cart_mapper_to_domain_with_items(self, mocker):
        orm_item = Mock(spec=ItemInCartOrm)
        orm_item.id = 1
        orm_item.item_id = 2
        orm_item.name = "Apple"
        orm_item.quantity = 3
        orm_item.available = True

        orm_cart = Mock(spec=CartOrm)
        orm_cart.id = 1
        orm_cart.price = 150.0
        orm_cart.items = [orm_item]

        domain_item = ItemInCart(id=1, item_id=2, name="Apple", quantity=3, available=True)
        mocker.patch('service.main.ItemInCartMapper.to_domain', return_value=domain_item)

        result = CartMapper.to_domain(orm_cart)

        assert isinstance(result, Cart)
        assert result.id == 1
        assert result.price == 150.0
        assert result.items == [domain_item]

    def test_item_mapper_to_orm_existing(self):
        domain_item = Item(id=1, name="Updated Apple", price=200.0, deleted=True)
        orm_item = MagicMock(spec=ItemOrm)
        orm_item.id = 1
        orm_item.name = "Apple"
        orm_item.price = 150.0
        orm_item.deleted = False

        result = ItemMapper.to_orm(domain_item, orm_item)

        assert result is orm_item
        assert result.name == "Updated Apple"
        assert result.price == 200.0
        assert result.deleted is True

    def test_item_in_cart_mapper_to_domain(self):
        orm_item_in_cart = MagicMock(spec=ItemInCartOrm)
        orm_item_in_cart.id = 1
        orm_item_in_cart.item_id = 2
        orm_item_in_cart.name = "Apple"
        orm_item_in_cart.quantity = 3
        orm_item_in_cart.available = True

        result = ItemInCartMapper.to_domain(orm_item_in_cart)

        assert isinstance(result, ItemInCart)
        assert result.id == 2
        assert result.item_id == 2
        assert result.name == "Apple"
        assert result.quantity == 3
        assert result.available is True

    def test_item_in_cart_mapper_to_orm_new(self):
        domain_item_in_cart = ItemInCart(id=None, item_id=2, name="Apple", quantity=3, available=True)

        result = ItemInCartMapper.to_orm(domain_item_in_cart)

        assert isinstance(result, ItemInCartOrm)
        assert result.item_id == 2
        assert result.name == "Apple"
        assert result.quantity == 3
        assert result.available is True

    def test_cart_mapper_to_orm_new(self):
        domain_cart = Cart(id=None, items=[], price=0.0)

        result = CartMapper.to_orm(domain_cart)

        assert isinstance(result, CartOrm)
        assert result.price == 0.0
        assert result.items == []

class TestCartAPI:
    @pytest.fixture
    def client(self, mocker):
        # Мокаем базу данных
        db = Mock(spec=Session)
        mock_session_local = Mock()
        mock_session_local.return_value = db
        mocker.patch('service.main.SessionLocal', mock_session_local)
        return TestClient(app)

    def test_create_cart(self, client, mocker):
        mock_cart = Cart(id=1, items=[], price=0.0)
        mocker.patch('service.main.SqlAlchemyCartRepository.create', return_value=mock_cart)

        response = client.post("/cart")

        assert response.status_code == HTTPStatus.CREATED
        assert response.json() == {"id": 1}
        assert response.headers["location"] == "/cart/1"

    def test_list_carts_default(self, client, mocker):
        mock_cart = Cart(id=1, items=[ItemInCart(id=1, item_id=1, name="Apple", quantity=1, available=True)], price=150.0)
        mocker.patch('service.main.SqlAlchemyCartRepository.get_all', return_value=[mock_cart])

        response = client.get("/cart?offset=0&limit=10")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [
            {
                "id": 1,
                "items": [{"id": 1, "name": "Apple", "quantity": 1, "available": True}],
                "price": 150.0
            }
        ]

    def test_get_cart_found(self, client, mocker):
        mock_cart = Cart(id=1, items=[], price=0.0)
        mocker.patch('service.main.SqlAlchemyCartRepository.find_by_id', return_value=mock_cart)

        response = client.get("/cart/1")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"id": 1, "items": [], "price": 0.0}

    def test_get_cart_not_found(self, client, mocker):
        mocker.patch('service.main.SqlAlchemyCartRepository.find_by_id', return_value=None)

        response = client.get("/cart/1")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Cart not found"}

class TestItemAPI:
    @pytest.fixture
    def client(self, mocker):
        db = Mock(spec=Session)
        mock_session_local = Mock()
        mock_session_local.return_value = db
        mocker.patch('service.main.SessionLocal', mock_session_local)
        return TestClient(app)

    def test_create_item(self, client, mocker):
        mock_item = Item(id=1, name="Apple", price=150.0, deleted=False)
        mocker.patch('service.main.SqlAlchemyItemRepository.create', return_value=mock_item)

        response = client.post("/item", json={"name": "Apple", "price": 150.0})

        assert response.status_code == HTTPStatus.CREATED
        assert response.json() == {"id": 1, "name": "Apple", "price": 150.0, "deleted": False}

    def test_get_item_found(self, client, mocker):
        mock_item = Item(id=1, name="Apple", price=150.0, deleted=False)
        mocker.patch('service.main.SqlAlchemyItemRepository.find_by_id', return_value=mock_item)

        response = client.get("/item/1")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"id": 1, "name": "Apple", "price": 150.0, "deleted": False}

    def test_get_item_not_found(self, client, mocker):
        mocker.patch('service.main.SqlAlchemyItemRepository.find_by_id', return_value=None)

        response = client.get("/item/1")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Item not found"}

    def test_get_all_items(self, client, mocker):
        mock_item = Item(id=1, name="Apple", price=150.0, deleted=False)
        mocker.patch('service.main.SqlAlchemyItemRepository.get_all', return_value=[mock_item])

        response = client.get("/item?offset=0&limit=10&min_price=100.0&max_price=200.0&show_deleted=false")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [{"id": 1, "name": "Apple", "price": 150.0, "deleted": False}]

    def test_update_item(self, client, mocker):
        mock_item = Item(id=1, name="Updated Apple", price=200.0, deleted=False)
        mocker.patch('service.main.SqlAlchemyItemRepository.update', return_value=mock_item)

        response = client.put("/item/1", json={"name": "Updated Apple", "price": 200.0})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"id": 1, "name": "Updated Apple", "price": 200.0, "deleted": False}

    def test_patch_item(self, client, mocker):
        mock_item = Item(id=1, name="Updated Apple", price=200.0, deleted=False)
        mocker.patch('service.main.SqlAlchemyItemRepository.find_by_id', return_value=Item(id=1, name="Apple", price=150.0, deleted=False))
        mocker.patch('service.main.SqlAlchemyItemRepository.update', return_value=mock_item)

        response = client.patch("/item/1", json={"price": 200.0, "name": "Updated Apple"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"id": 1, "name": "Updated Apple", "price": 200.0, "deleted": False}

    def test_delete_item(self, client, mocker):
        mocker.patch('service.main.SqlAlchemyItemRepository.delete', return_value=None)

        response = client.delete("/item/1")

        assert response.status_code == HTTPStatus.OK

    def test_add_item_to_cart(self, client, mocker):
        mock_cart = Cart(id=1, items=[ItemInCart(id=1, item_id=1, name="Apple", quantity=1, available=True)], price=150.0)
        mocker.patch('service.main.SqlAlchemyCartRepository.add_item', return_value=mock_cart)

        response = client.post("/cart/1/add/1")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {
            "id": 1,
            "items": [{"id": 1, "name": "Apple", "quantity": 1, "available": True}],
            "price": 150.0
        }

    def test_add_item_to_cart_not_found(self, client, mocker):
        mocker.patch(
            'service.main.SqlAlchemyCartRepository.add_item',
            side_effect=ValueError("Cart or item not found")
        )
        response = client.post("/cart/999/add/999")
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "Cart or item not found"}