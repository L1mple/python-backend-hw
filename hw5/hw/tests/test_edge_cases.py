import pytest
from shop_api.cart.store import queries as cart_queries
from shop_api.item.store import queries as item_queries
from shop_api.item.store.models import ItemInfo, ItemEntity, ItemDB

class TestEdgeCases:
    def test_add_item_to_nonexistent_cart(self, db_session):
        """Test ajout d'item à un panier qui n'existe pas"""
        # Créer un item valide
        item_info = ItemInfo(name="Test", price=10.0, deleted=False)
        db_item = ItemDB(name=item_info.name, price=item_info.price, deleted=item_info.deleted)
        db_session.add(db_item)
        db_session.commit()
        db_session.refresh(db_item)
        
        item_entity = ItemEntity(id=db_item.id, info=item_info)
        
        # Essayer d'ajouter à un panier inexistant
        result = cart_queries.add(999999, item_entity, db_session)
        assert result is None  # Devrait retourner None

    def test_get_many_carts_edge_cases(self, db_session):
        """Test get_many avec des filtres extrêmes"""
        # Filtres qui ne matchent rien
        carts = list(cart_queries.get_many(db_session, min_price=1000000))
        assert len(carts) == 0
        
        # Filtres avec valeurs None
        carts = list(cart_queries.get_many(db_session, min_price=None, max_price=None))
        assert isinstance(carts, list)

    def test_cart_queries_none_handling(self, db_session):
        """Test gestion des valeurs None dans les queries"""
        # get_one avec ID None
        result = cart_queries.get_one(None, db_session)
        assert result is None

    def test_add_nonexistent_item_to_cart(self, db_session):
        """Test ajout d'un item qui n'existe pas en base"""
        cart = cart_queries.create(db_session)
        
        # Créer une entité item avec un ID qui n'existe pas en base
        fake_item_entity = ItemEntity(id=999999, info=ItemInfo(name="Fake", price=10.0, deleted=False))
        
        result = cart_queries.add(cart.id, fake_item_entity, db_session)
        assert result is None