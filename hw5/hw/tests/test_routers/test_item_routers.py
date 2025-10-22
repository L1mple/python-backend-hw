import pytest
from fastapi import status
from shop_api.item.store.models import ItemInfo

class TestItemRouters:
    def test_create_item_success(self, client, db_session):
        """Test la création d'un item via API"""
        response = client.post(
            "/item/",
            json={"name": "API Test Item", "price": 99.99}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "API Test Item"
        assert data["price"] == 99.99
        assert data["deleted"] is False
        assert "id" in data
        assert "location" in response.headers
    
    def test_create_item_invalid_data(self, client):
        """Test la création avec données invalides"""
        # Prix négatif
        response = client.post(
            "/item/",
            json={"name": "Test", "price": -10.0}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        
        # Données manquantes
        response = client.post(
            "/item/",
            json={"name": "Test"}  # price manquant
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    def test_get_item_by_id_success(self, client, db_session):
        """Test la récupération d'un item existant"""
        # Crée un item d'abord
        create_response = client.post("/item/", json={"name": "Get Test", "price": 50.0})
        item_id = create_response.json()["id"]
        
        # Récupère
        response = client.get(f"/item/{item_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Get Test"
        assert data["price"] == 50.0
        assert data["id"] == item_id
    
    def test_get_item_by_id_not_found(self, client):
        """Test la récupération d'un item inexistant"""
        response = client.get("/item/9999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_item_list(self, client, db_session):
        """Test la liste des items avec filtres"""
        # Crée quelques items
        items_data = [
            {"name": "Item10", "price": 10.0},
            {"name": "Item30", "price": 30.0},
            {"name": "Item50", "price": 50.0}
        ]
        for item_data in items_data:
            client.post("/item/", json=item_data)
        
        # Récupère tous
        response = client.get("/item/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
        
        # Avec filtre prix min
        response = client.get("/item/?min_price=25.0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Vérifie que tous les items ont prix >= 25
        for item in data:
            assert item["price"] >= 25.0
    
    def test_update_item_success(self, client, db_session):
        """Test la mise à jour complète d'un item"""
        # Crée un item
        create_response = client.post("/item/", json={"name": "Original", "price": 10.0})
        item_id = create_response.json()["id"]
        
        # Met à jour
        response = client.put(
            f"/item/{item_id}",
            json={"name": "Updated", "price": 20.0, "deleted": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated"
        assert data["price"] == 20.0
        assert data["deleted"] is True
    
    def test_update_item_not_found(self, client):
        """Test la mise à jour d'un item inexistant"""
        response = client.put(
            "/item/9999",
            json={"name": "Test", "price": 10.0}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_patch_item_success(self, client, db_session):
        """Test la mise à jour partielle"""
        # Crée un item
        create_response = client.post("/item/", json={"name": "Original", "price": 10.0})
        item_id = create_response.json()["id"]
        
        # Patch seulement le nom
        response = client.patch(
            f"/item/{item_id}",
            json={"name": "Patched"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Patched"
        assert data["price"] == 10.0  # Inchangé
    
    def test_patch_item_not_found(self, client):
        """Test le patch d'un item inexistant"""
        response = client.patch("/item/9999", json={"name": "Test"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_item_success(self, client, db_session):
        """Test la suppression d'un item"""
        # Crée un item
        create_response = client.post("/item/", json={"name": "To Delete", "price": 10.0})
        item_id = create_response.json()["id"]
        
        # Supprime
        response = client.delete(f"/item/{item_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Vérifie qu'il n'existe plus
        get_response = client.get(f"/item/{item_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND