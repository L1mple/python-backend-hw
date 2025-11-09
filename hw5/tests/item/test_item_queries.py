import pytest
from shop_api.item.store import queries
from shop_api.item.store.schemas import ItemInfo, PatchItemInfo


@pytest.fixture
def sample_item(session):
    return queries.add(session, ItemInfo(name="Pencil", price=2.0))


def test_add_item(session):
    item = queries.add(session, ItemInfo(name="Book", price=10.0))
    assert item.id > 0
    assert item.info.name == "Book"


def test_get_one(session, sample_item):
    found = queries.get_one(session, sample_item.id)
    assert found.info.name == "Pencil"


def test_get_many(session):
    queries.add(session, ItemInfo(name="Pen", price=3.0))
    queries.add(session, ItemInfo(name="Notebook", price=7.0))
    items = list(queries.get_many(session, min_price=5))
    assert len(items) == 1
    assert items[0].info.name == "Notebook"


def test_update_item(session, sample_item):
    updated_info = ItemInfo(name="Pen", price=4.5)
    updated = queries.update(session, sample_item.id, updated_info)
    assert updated.info.price == 4.5


def test_patch_item(session, sample_item):
    patched = queries.patch(session, sample_item.id, PatchItemInfo(price=5.0))
    assert patched.info.price == 5.0


def test_delete_item(session, sample_item):
    assert queries.delete(session, sample_item.id)
    assert queries.get_one(session, sample_item.id) is None


def test_delete_nonexistent(session):
    assert queries.delete(session, 999) is False
