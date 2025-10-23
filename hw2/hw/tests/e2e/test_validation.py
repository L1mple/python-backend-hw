"""E2E tests for input validation

Tests that API properly validates input data and rejects invalid requests.
"""
import pytest
from http import HTTPStatus


class TestItemValidation:
    """Tests for item input validation"""

    async def test_create_item_with_negative_price(self, client):
        """Test that negative price is rejected"""
        response = await client.post(
            "/item/",
            json={"name": "Invalid Item", "price": -10.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        error = response.json()
        assert "price" in str(error).lower()

    async def test_create_item_with_zero_price_rejected(self, client):
        """Test that zero price is rejected (price must be > 0)"""
        response = await client.post(
            "/item/",
            json={"name": "Free Item", "price": 0.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        error = response.json()
        assert "price" in str(error).lower()

    async def test_create_item_with_empty_name(self, client):
        """Test that empty name is rejected"""
        response = await client.post(
            "/item/",
            json={"name": "", "price": 10.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        error = response.json()
        assert "name" in str(error).lower()

    async def test_create_item_with_too_long_name(self, client):
        """Test that very long name is rejected"""
        long_name = "A" * 256  # Max is 255
        response = await client.post(
            "/item/",
            json={"name": long_name, "price": 10.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        error = response.json()
        assert "name" in str(error).lower()

    async def test_create_item_with_invalid_price_type(self, client):
        """Test that non-numeric price is rejected"""
        response = await client.post(
            "/item/",
            json={"name": "Test", "price": "not_a_number"}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_create_item_missing_required_fields(self, client):
        """Test that missing required fields are rejected"""
        # Missing price
        response = await client.post(
            "/item/",
            json={"name": "Test"}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        # Missing name
        response = await client.post(
            "/item/",
            json={"price": 10.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_patch_item_with_negative_price(self, client):
        """Test that patch with negative price is rejected"""
        # Create item first
        create_resp = await client.post(
            "/item/",
            json={"name": "Test", "price": 10.0}
        )
        item_id = create_resp.json()["id"]

        # Try to patch with negative price
        response = await client.patch(
            f"/item/{item_id}",
            json={"price": -5.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_patch_item_with_empty_name(self, client):
        """Test that patch with empty name is rejected"""
        # Create item first
        create_resp = await client.post(
            "/item/",
            json={"name": "Test", "price": 10.0}
        )
        item_id = create_resp.json()["id"]

        # Try to patch with empty name
        response = await client.patch(
            f"/item/{item_id}",
            json={"name": ""}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_put_item_with_invalid_data(self, client):
        """Test that PUT with invalid data is rejected"""
        response = await client.put(
            "/item/1",
            json={"name": "", "price": -10.0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestValidItemsAfterValidation:
    """Tests to ensure valid items still work after adding validation"""

    async def test_create_item_with_valid_data_still_works(self, client):
        """Test that valid items are still accepted"""
        response = await client.post(
            "/item/",
            json={"name": "Valid Item", "price": 99.99}
        )
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["name"] == "Valid Item"
        assert data["price"] == 99.99

    async def test_create_item_with_minimum_valid_name(self, client):
        """Test that single character name is accepted"""
        response = await client.post(
            "/item/",
            json={"name": "A", "price": 1.0}
        )
        assert response.status_code == HTTPStatus.CREATED

    async def test_create_item_with_maximum_valid_name(self, client):
        """Test that 255 character name is accepted"""
        max_name = "A" * 255
        response = await client.post(
            "/item/",
            json={"name": max_name, "price": 1.0}
        )
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert len(data["name"]) == 255

    async def test_create_item_with_small_positive_price(self, client):
        """Test that very small positive price is accepted"""
        response = await client.post(
            "/item/",
            json={"name": "Penny", "price": 0.01}
        )
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["price"] == 0.01
