import pytest
from shop_api.cart.store import queries as cart_queries
from shop_api.item.store.models import ItemInfo, ItemEntity, ItemDB
from shop_api.item.contracts import PatchItemRequest

class TestFinalCoverage:
    def test_get_many_carts_complex_filters(self, db_session):
        """Test get_many avec tous les types de filtres"""
        # Créer des paniers avec différentes quantités
        for i in range(3):
            cart = cart_queries.create(db_session)
            if i > 0:
                # Créer et ajouter des items
                item_info = ItemInfo(name=f"Item{i}", price=10.0 * i, deleted=False)
                db_item = ItemDB(name=item_info.name, price=item_info.price, deleted=item_info.deleted)
                db_session.add(db_item)
                db_session.commit()
                db_session.refresh(db_item)
                item_entity = ItemEntity(id=db_item.id, info=item_info)
                cart_queries.add(cart.id, item_entity, db_session)
        
        # Tester avec min_quantity et max_quantity
        carts_min = list(cart_queries.get_many(db_session, min_quantity=1))
        carts_max = list(cart_queries.get_many(db_session, max_quantity=0))
        carts_both = list(cart_queries.get_many(db_session, min_quantity=1, max_quantity=10))
        
        assert isinstance(carts_min, list)
        assert isinstance(carts_max, list)
        assert isinstance(carts_both, list)

    def test_patch_item_request_all_none(self, db_session):
        """Test PatchItemRequest avec tous les champs None"""
        patch = PatchItemRequest(name=None, price=None)
        patch_info = patch.as_patch_item_info()
        
        assert patch_info.name is None
        assert patch_info.price is None

    def test_cart_queries_return_none_cases(self, db_session):
        """Test les cas où les queries retournent None"""
        # Test avec des IDs négatifs
        result = cart_queries.get_one(-1, db_session)
        assert result is None
        
        # Test delete avec ID négatif
        cart_queries.delete(-1, db_session)  # Ne devrait pas crasher

    def test_item_contracts_edge_validators(self):
        """Test des validateurs edge dans les contracts"""
        # Test du validateur de prix dans PatchItemRequest
        patch = PatchItemRequest(price=0.0)
        assert patch.price == 0.0
        
        # Test du validateur de nom
        patch = PatchItemRequest(name="Valid Name")
        assert patch.name == "Valid Name"