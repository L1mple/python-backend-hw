from shop_api.item.store.schemas import ItemInfo, ItemEntity, PatchItemInfo


def test_iteminfo_model():
    info = ItemInfo(name="Book", price=9.9)
    assert not info.deleted
    assert info.name == "Book"


def test_patchiteminfo_model():
    patch = PatchItemInfo(price=4.4)
    assert patch.price == 4.4


def test_itementity_model():
    info = ItemInfo(name="Pencil", price=2.0)
    entity = ItemEntity(id=1, info=info)
    assert entity.info.name == "Pencil"
