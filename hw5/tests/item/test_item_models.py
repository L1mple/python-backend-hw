from shop_api.item.store.models import Item


def test_item_model_fields(session):
    item = Item(name="Marker", price=1.5)
    session.add(item)
    session.commit()
    result = session.query(Item).first()
    assert result.name == "Marker"
    assert result.price == 1.5
    assert result.deleted is False
