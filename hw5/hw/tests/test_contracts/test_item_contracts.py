import pytest
from pydantic import ValidationError
from shop_api.item.contracts import ItemRequest, ItemResponse, PatchItemRequest
from shop_api.item.store.models import ItemEntity, ItemInfo

class TestItemContracts:
    def test_item_request_valid(self):
        """Test ItemRequest valide"""
        request = ItemRequest(name="Test Item", price=100.0)
        
        assert request.name == "Test Item"
        assert request.price == 100.0
        assert request.deleted is False  # Valeur par défaut
    
    def test_item_request_invalid(self):

        with pytest.raises(ValueError):
            ItemRequest(name="Test", price=-10.0)
        
        # Nom vide
        with pytest.raises(ValueError):
            ItemRequest(name="", price=10.0)
        
        # Données manquantes - Pydantic lève ValidationError
        with pytest.raises(ValidationError):
            ItemRequest(name="Test")  # price manquant

    
    def test_item_response_from_entity(self):
        """Test la conversion d'Entity vers Response"""
        entity = ItemEntity(
            id=1, 
            info=ItemInfo(name="Test", price=50.0, deleted=False)
        )
        
        response = ItemResponse.from_entity(entity)
        
        assert response.id == 1
        assert response.name == "Test"
        assert response.price == 50.0
        assert response.deleted is False
    
    def test_item_request_as_item_info(self):
        """Test la conversion vers ItemInfo"""
        request = ItemRequest(name="Test", price=75.0, deleted=True)
        info = request.as_item_info()
        
        assert info.name == "Test"
        assert info.price == 75.0
        assert info.deleted is True
    
    def test_patch_item_request(self):
        """Test PatchItemRequest"""
        # Partiel
        patch = PatchItemRequest(name="Nouveau nom")
        assert patch.name == "Nouveau nom"
        assert patch.price is None
        
        # Conversion vers PatchItemInfo
        patch_info = patch.as_patch_item_info()
        assert patch_info.name == "Nouveau nom"
        assert patch_info.price is None
    
    def test_patch_item_request_extra_fields(self):
        """Test que les champs supplémentaires sont interdits"""
        with pytest.raises(ValidationError):
            PatchItemRequest(name="Test", invalid_field="value")