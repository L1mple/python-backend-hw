from shop_api.item.contracts import ItemResponse, ItemRequest, PatchItemRequest
from shop_api.item.store.schemas import ItemEntity, ItemInfo


def test_itemresponse_from_entity():
    entity = ItemEntity(id=1, info=ItemInfo(name="Marker", price=1.5))
    resp = ItemResponse.from_entity(entity)
    assert resp.name == "Marker"


def test_itemrequest_to_info():
    req = ItemRequest(name="Book", price=12.0, deleted=False)
    info = req.as_item_info()
    assert info.name == "Book"


def test_patchitemrequest_to_patch_info():
    req = PatchItemRequest(name="Pen", price=5.0)
    patch = req.as_patch_item_info()
    assert patch.price == 5.0
