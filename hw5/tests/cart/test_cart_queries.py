import pytest
from shop_api.cart.store import queries as cart_queries
from shop_api.item.store import queries as item_queries
from shop_api.item.store.schemas import ItemInfo, ItemEntity


@pytest.fixture
def sample_item(session):
    info = ItemInfo(name="Book", price=10.0)
    item = item_queries.add(session, info)
    return item


def test_create_cart(session):
    cart = cart_queries.create(session)
    assert cart.id > 0
    assert cart.price == 0.0
    assert cart.items == []


def test_add_item(session, sample_item):
    cart = cart_queries.create(session)
    updated = cart_queries.add(session, cart.id, sample_item)
    assert updated.price == 10.0
    assert updated.items[0].quantity == 1


def test_add_same_item_increments_quantity(session, sample_item):
    cart = cart_queries.create(session)
    cart_queries.add(session, cart.id, sample_item)
    updated = cart_queries.add(session, cart.id, sample_item)
    assert updated.items[0].quantity == 2
    assert updated.price == 20.0


def test_add_deleted_item_unavailable(session):

    cart = cart_queries.create(session)
    deleted_item = ItemEntity(id=1, info=ItemInfo(name="Old", price=5, deleted=True))
    result = cart_queries.add(session, cart.id, deleted_item)
    assert result.items[0].available is False


def test_get_one(session, sample_item):
    cart = cart_queries.create(session)
    cart_queries.add(session, cart.id, sample_item)
    found = cart_queries.get_one(session, cart.id)
    assert found.id == cart.id
    assert found.price == 10.0


def test_get_many_with_filters(session, sample_item):
    c1 = cart_queries.create(session)
    c2 = cart_queries.create(session)
    cart_queries.add(session, c1.id, sample_item)
    cart_queries.add(session, c2.id, sample_item)
    cart_queries.add(session, c2.id, sample_item)
    result = list(cart_queries.get_many(session, min_price=15))
    assert len(result) == 1
    assert result[0].id == c2.id


def test_delete_cart(session):
    cart = cart_queries.create(session)
    assert cart_queries.delete(session, cart.id)
    assert not cart_queries.get_one(session, cart.id)


def test_add_to_nonexistent_cart_returns_none(session, sample_item):
    # cart_id не существует
    result = cart_queries.add(session, 999, sample_item)
    assert result is None


def test_delete_nonexistent_cart_returns_false(session):
    # Корзины с таким ID нет
    result = cart_queries.delete(session, 999)
    assert result is False


def test_get_many_with_quantity_filters(session, sample_item):
    c1 = cart_queries.create(session)
    c2 = cart_queries.create(session)
    # в первой корзине 1 товар
    cart_queries.add(session, c1.id, sample_item)
    # во второй — 3
    cart_queries.add(session, c2.id, sample_item)
    cart_queries.add(session, c2.id, sample_item)
    cart_queries.add(session, c2.id, sample_item)

    result_min = list(cart_queries.get_many(session, min_quantity=2))
    result_max = list(cart_queries.get_many(session, max_quantity=2))

    # Проверяем, что фильтры работают
    assert all(sum(i.quantity for i in c.items) >= 2 for c in result_min)
    assert all(sum(i.quantity for i in c.items) <= 2 for c in result_max)
