import pytest
from pydantic import ValidationError
from shop_api.item.contracts import ItemRequest, PatchItemRequest

class TestEdgeContracts:
    def test_item_request_edge_cases(self):
        """Test des cas limites pour ItemRequest"""
        # Prix à 0 (devroit être valide)
        request = ItemRequest(name="Free Item", price=0.0)
        assert request.price == 0.0
        
        # Prix très élevé
        request = ItemRequest(name="Expensive", price=999999.99)
        assert request.price == 999999.99
        
        # Nom avec espaces (devrait être strippé par le validateur)
        request = ItemRequest(name="  Test Item  ", price=10.0)
        assert request.name == "Test Item"

    def test_patch_item_request_edge_cases(self):
        """Test des cas limites pour PatchItemRequest"""
        # Tous les champs None
        patch = PatchItemRequest()
        assert patch.name is None
        assert patch.price is None
        
        # Prix à 0
        patch = PatchItemRequest(price=0.0)
        assert patch.price == 0.0
        
        # Nom vide (devrait être validé)
        with pytest.raises(ValueError):
            PatchItemRequest(name="")

    def test_item_request_boundary_values(self):
        """Test des valeurs aux limites"""
        # Prix limite (0)
        request = ItemRequest(name="Test", price=0.0)
        assert request.price == 0.0
        
        # Nom très long
        long_name = "A" * 100
        request = ItemRequest(name=long_name, price=10.0)
        assert request.name == long_name