import pytest
from fastapi import status

class TestIntegration:
    def test_complete_shopping_flow(self, client, db_session):
        """Test un flux complet d'achat"""
        # 1. Crée quelques items
        items_data = [
            {"name": "Laptop", "price": 999.99},
            {"name": "Mouse", "price": 29.99},
            {"name": "Keyboard", "price": 79.99}
        ]
        
        item_ids = []
        for item_data in items_data:
            response = client.post("/item/", json=item_data)
            assert response.status_code == status.HTTP_201_CREATED
            item_ids.append(response.json()["id"])
        
        # 2. Crée un panier
        cart_response = client.post("/cart/")
        assert cart_response.status_code == status.HTTP_201_CREATED
        cart_id = cart_response.json()["id"]
        
        # 3. Ajoute des items au panier
        # Ajoute le laptop
        response = client.post(f"/cart/{cart_id}/add/{item_ids[0]}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["price"] == 999.99
        
        # Ajoute deux souris
        response = client.post(f"/cart/{cart_id}/add/{item_ids[1]}")
        assert response.status_code == status.HTTP_200_OK
        response = client.post(f"/cart/{cart_id}/add/{item_ids[1]}")
        assert response.status_code == status.HTTP_200_OK
        
        # 4. Vérifie le panier final
        cart_response = client.get(f"/cart/{cart_id}")
        assert cart_response.status_code == status.HTTP_200_OK
        cart_data = cart_response.json()
        
        assert len(cart_data["items"]) == 2  # Laptop + Souris (même item mais agrégé)
        assert cart_data["price"] == 999.99 + (29.99 * 2)  # 1059.97
        
        # Trouve l'item souris dans le panier
        mouse_item = next(item for item in cart_data["items"] if item["name"] == "Mouse")
        assert mouse_item["quantity"] == 2
    
    def test_item_lifecycle(self, client, db_session):
        """Test cycle de vie complet d'un item"""
        # 1. Création
        create_response = client.post("/item/", json={"name": "Test Lifecycle", "price": 100.0})
        assert create_response.status_code == status.HTTP_201_CREATED
        item_id = create_response.json()["id"]
        
        # 2. Lecture
        get_response = client.get(f"/item/{item_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["name"] == "Test Lifecycle"
        
        # 3. Mise à jour partielle
        patch_response = client.patch(f"/item/{item_id}", json={"price": 150.0})
        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.json()["price"] == 150.0
        assert patch_response.json()["name"] == "Test Lifecycle"  # Inchangé
        
        # 4. Mise à jour complète
        put_response = client.put(
            f"/item/{item_id}", 
            json={"name": "Updated Lifecycle", "price": 200.0, "deleted": True}
        )
        assert put_response.status_code == status.HTTP_200_OK
        assert put_response.json()["name"] == "Updated Lifecycle"
        assert put_response.json()["deleted"] is True
        
        # 5. Suppression
        delete_response = client.delete(f"/item/{item_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # 6. Vérifie que l'item n'existe plus
        final_get = client.get(f"/item/{item_id}")
        assert final_get.status_code == status.HTTP_404_NOT_FOUND