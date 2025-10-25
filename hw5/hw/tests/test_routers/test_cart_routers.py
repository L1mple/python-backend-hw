import pytest
from fastapi import status

class TestCartRouters:
    def test_create_cart_success(self, client, db_session):
        """Test la création d'un panier via API"""
        response = client.post("/cart/")
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["items"] == []
        assert data["price"] == 0.0
        assert "location" in response.headers
    
    def test_get_cart_by_id_success(self, client, db_session):
        """Test la récupération d'un panier existant"""
        # Crée un panier d'abord
        create_response = client.post("/cart/")
        cart_id = create_response.json()["id"]
        
        # Récupère
        response = client.get(f"/cart/{cart_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == cart_id
        assert data["items"] == []
        assert data["price"] == 0.0
    
    def test_get_cart_by_id_not_found(self, client):
        """Test la récupération d'un panier inexistant"""
        response = client.get("/cart/9999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_cart_list(self, client, db_session):
        """Test la liste des paniers"""
        # Crée quelques paniers
        for i in range(3):
            client.post("/cart/")
        
        response = client.get("/cart/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
    
    def test_add_item_to_cart_success(self, client, db_session):
        """Test l'ajout d'un item au panier"""
        # Crée un panier
        cart_response = client.post("/cart/")
        cart_id = cart_response.json()["id"]
        
        # Crée un item
        item_response = client.post("/item/", json={"name": "Cart Item", "price": 25.0})
        item_id = item_response.json()["id"]
        
        # Ajoute au panier
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Cart Item"
        assert data["items"][0]["quantity"] == 1
        assert data["price"] == 25.0
    
    def test_add_item_to_cart_cart_not_found(self, client, db_session):
        """Test l'ajout avec panier inexistant"""
        # Crée un item
        item_response = client.post("/item/", json={"name": "Test", "price": 10.0})
        item_id = item_response.json()["id"]
        
        response = client.post(f"/cart/9999/add/{item_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_add_item_to_cart_item_not_found(self, client, db_session):
        """Test l'ajout avec item inexistant"""
        # Crée un panier
        cart_response = client.post("/cart/")
        cart_id = cart_response.json()["id"]
        
        response = client.post(f"/cart/{cart_id}/add/9999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_cart_success(self, client, db_session):
        """Test la suppression d'un panier"""
        # Crée un panier
        create_response = client.post("/cart/")
        cart_id = create_response.json()["id"]
        
        # Supprime
        response = client.delete(f"/cart/{cart_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Vérifie qu'il n'existe plus
        get_response = client.get(f"/cart/{cart_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND