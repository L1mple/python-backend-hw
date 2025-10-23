import pytest
from shop_api.item.store.models import ItemInfo, ItemEntity, PatchItemInfo

class TestItemModels:
    def test_item_info_creation(self):
        """Test la création d'un ItemInfo"""
        info = ItemInfo(name="Test Item", price=99.99, deleted=False)
        
        assert info.name == "Test Item"
        assert info.price == 99.99
        assert info.deleted is False
    
    def test_item_entity_creation(self):
        """Test la création d'un ItemEntity"""
        info = ItemInfo(name="Test", price=50.0, deleted=True)
        entity = ItemEntity(id=1, info=info)
        
        assert entity.id == 1
        assert entity.info.name == "Test"
        assert entity.info.price == 50.0
        assert entity.info.deleted is True
    
    def test_patch_item_info_partial(self):
        """Test PatchItemInfo avec valeurs partielles"""
        # Seulement le nom
        patch1 = PatchItemInfo(name="Nouveau nom")
        assert patch1.name == "Nouveau nom"
        assert patch1.price is None
        
        # Seulement le prix
        patch2 = PatchItemInfo(price=150.0)
        assert patch2.price == 150.0
        assert patch2.name is None
        
        # Les deux
        patch3 = PatchItemInfo(name="Test", price=200.0)
        assert patch3.name == "Test"
        assert patch3.price == 200.0