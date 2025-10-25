import pytest
from shop_api.item.store import queries
from shop_api.item.store.models import ItemInfo, PatchItemInfo

class TestItemQueries:
    def test_add_item(self, db_session):
        """Test l'ajout d'un item"""
        info = ItemInfo(name="Test Item", price=100.0, deleted=False)
        
        entity = queries.add(info, db_session)
        
        assert entity.info.name == "Test Item"
        assert entity.info.price == 100.0
        assert entity.id is not None
        
        # Vérifie en base
        db_item = db_session.query(queries.ItemDB).filter_by(id=entity.id).first()
        assert db_item.name == "Test Item"
    
    def test_get_one_existing(self, db_session):
        """Test la récupération d'un item existant"""
        # Crée un item d'abord
        info = ItemInfo(name="Get Test", price=50.0, deleted=False)
        created = queries.add(info, db_session)
        
        # Récupère
        entity = queries.get_one(created.id, db_session)
        
        assert entity is not None
        assert entity.id == created.id
        assert entity.info.name == "Get Test"
    
    def test_get_one_nonexistent(self, db_session):
        """Test la récupération d'un item inexistant"""
        entity = queries.get_one(9999, db_session)
        assert entity is None
    
    def test_get_many(self, db_session):
        """Test la récupération de plusieurs items"""
        # Crée quelques items
        items_data = [
            ItemInfo(name="Item1", price=10.0, deleted=False),
            ItemInfo(name="Item2", price=20.0, deleted=False),
            ItemInfo(name="Item3", price=30.0, deleted=True)  # Supprimé
        ]
        
        for info in items_data:
            queries.add(info, db_session)
        
        # Récupère sans les supprimés
        entities = list(queries.get_many(db_session, show_deleted=False))
        assert len(entities) == 2
        
        # Récupère avec les supprimés
        entities = list(queries.get_many(db_session, show_deleted=True))
        assert len(entities) == 3
    
    def test_get_many_with_filters(self, db_session):
        """Test les filtres prix"""
        # Crée des items avec différents prix
        prices = [10.0, 25.0, 50.0, 75.0, 100.0]
        for price in prices:
            queries.add(ItemInfo(name=f"Item{price}", price=price, deleted=False), db_session)
        
        # Filtre prix min
        entities = list(queries.get_many(db_session, min_price=30.0))
        assert len(entities) == 3  # 50, 75, 100
        
        # Filtre prix max
        entities = list(queries.get_many(db_session, max_price=30.0))
        assert len(entities) == 2  # 10, 25
        
        # Filtre min et max
        entities = list(queries.get_many(db_session, min_price=20.0, max_price=60.0))
        assert len(entities) == 2  # 25, 50
    
    def test_update_item(self, db_session):
        """Test la mise à jour complète d'un item"""
        # Crée un item
        original = queries.add(ItemInfo(name="Original", price=10.0, deleted=False), db_session)
        
        # Met à jour
        new_info = ItemInfo(name="Updated", price=20.0, deleted=True)
        updated = queries.update(original.id, new_info, db_session)
        
        assert updated is not None
        assert updated.info.name == "Updated"
        assert updated.info.price == 20.0
        assert updated.info.deleted is True
    
    def test_update_nonexistent(self, db_session):
        """Test la mise à jour d'un item inexistant"""
        info = ItemInfo(name="Test", price=10.0, deleted=False)
        result = queries.update(9999, info, db_session)
        assert result is None
    
    def test_patch_item(self, db_session):
        """Test la mise à jour partielle"""
        # Crée un item
        original = queries.add(ItemInfo(name="Original", price=10.0, deleted=False), db_session)
        
        # Patch seulement le nom
        patch_info = PatchItemInfo(name="Patched")
        patched = queries.patch(original.id, patch_info, db_session)
        
        assert patched is not None
        assert patched.info.name == "Patched"
        assert patched.info.price == 10.0  # Inchangé
    
    def test_delete_item(self, db_session):
        """Test la suppression d'un item"""
        # Crée un item
        entity = queries.add(ItemInfo(name="To Delete", price=10.0, deleted=False), db_session)
        
        # Supprime
        queries.delete(entity.id, db_session)
        
        # Vérifie qu'il n'existe plus
        result = queries.get_one(entity.id, db_session)
        assert result is None