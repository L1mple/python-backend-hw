import pytest
from fastapi import status

class TestMain:
    def test_root_endpoint(self, client):
        """Test le endpoint racine"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "API Shop is running"}
    
    def test_404_for_unknown_route(self, client):
        """Test qu'une route inconnue retourne 404"""
        response = client.get("/unknown-route")
        assert response.status_code == status.HTTP_404_NOT_FOUND