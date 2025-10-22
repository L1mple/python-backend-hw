import pytest
from shop_api.cart.store import queries
from shop_api.item.store.models import ItemInfo, ItemEntity, ItemDB

class TestCartQueries:

    def test_create_cart(self, db_session):
        """Test la création d'un panier"""
        entity = queries.create(db_session)
        assert entity.id is not None
        assert entity.info.items == []
        assert entity.info.price == 0.0

    def test_get_one_cart(self, db_session):
        """Test la récupération d'un panier"""
        created = queries.create(db_session)
        entity = queries.get_one(created.id, db_session)
        assert entity is not None
        assert entity.id == created.id
        assert entity.info.price == 0.0

    def test_add_item_to_cart(self, db_session):
        """Test l'ajout d'un item au panier"""
        item_info = ItemInfo(name="Test Item", price=25.0, deleted=False)
        db_item = ItemDB(name=item_info.name, price=item_info.price, deleted=item_info.deleted)
        db_session.add(db_item)
        db_session.commit()
        db_session.refresh(db_item)

        cart = queries.create(db_session)
        item_entity = ItemEntity(id=db_item.id, info=item_info)
        updated_cart = queries.add(cart.id, item_entity, db_session)

        assert updated_cart is not None
        assert len(updated_cart.info.items) == 1
        assert updated_cart.info.items[0].name == "Test Item"
        assert updated_cart.info.items[0].quantity == 1
        assert updated_cart.info.price == 25.0

    def test_add_item_twice_increases_quantity(self, db_session):
        """Test que l'ajout du même item incrémente la quantité"""
        item_info = ItemInfo(name="Test", price=10.0, deleted=False)
        db_item = ItemDB(name=item_info.name, price=item_info.price, deleted=item_info.deleted)
        db_session.add(db_item)
        db_session.commit()
        db_session.refresh(db_item)

        cart = queries.create(db_session)
        item_entity = ItemEntity(id=db_item.id, info=item_info)
        queries.add(cart.id, item_entity, db_session)
        updated_cart = queries.add(cart.id, item_entity, db_session)

        assert len(updated_cart.info.items) == 1
        assert updated_cart.info.items[0].quantity == 2
        assert updated_cart.info.price == 20.0

    def test_get_many_carts_with_filters(self, db_session):
        """Test la récupération avec filtres"""
        items = []
        for i in range(3):
            db_item = ItemDB(name=f"Item{i}", price=10.0 * i, deleted=False)
            db_session.add(db_item)
            items.append(db_item)
        db_session.commit()
        for item in items:
            db_session.refresh(item)

        carts = []
        for i in range(3):
            cart = queries.create(db_session)
            if i > 0:
                item_entity = ItemEntity(
                    id=items[i].id,
                    info=ItemInfo(name=items[i].name, price=items[i].price, deleted=False)
                )
                queries.add(cart.id, item_entity, db_session)
            carts.append(cart)

        filtered_carts = list(queries.get_many(db_session, min_price=10.0))
        assert len(filtered_carts) == 2

    def test_delete_cart(self, db_session):
        """Test la suppression d'un panier"""
        cart = queries.create(db_session)
        queries.delete(cart.id, db_session)
        result = queries.get_one(cart.id, db_session)
        assert result is None
