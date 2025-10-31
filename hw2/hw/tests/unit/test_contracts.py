"""Unit tests for API contracts (Pydantic models)

Tests the data validation and transformation logic in shop_api/api/shop/contracts.py
"""
import pytest
from pydantic import ValidationError

from shop_api.api.shop.contracts import (
    ItemResponse,
    ItemRequest,
    PatchItemRequest,
    CartResponse,
    CartRequest,
    PatchCartRequest,
)
from shop_api.data.models import ItemEntity, ItemInfo, CartEntity, CartInfo, CartItemInfo


class TestItemContracts:
    """Tests for Item contracts (Pydantic models)"""

    def test_item_response_from_entity(self):
        """Test ItemResponse.from_entity method"""
        entity = ItemEntity(
            id=1,
            info=ItemInfo(name="Test Item", price=50.0, deleted=False)
        )

        response = ItemResponse.from_entity(entity)
        assert response.id == 1
        assert response.name == "Test Item"
        assert response.price == 50.0
        assert response.deleted is False

    def test_item_response_from_entity_with_deleted(self):
        """Test ItemResponse.from_entity with deleted item"""
        entity = ItemEntity(
            id=1,
            info=ItemInfo(name="Deleted", price=10.0, deleted=True)
        )

        response = ItemResponse.from_entity(entity)
        assert response.id == 1
        assert response.deleted is True

    def test_item_request_as_item_info(self):
        """Test ItemRequest.as_item_info method"""
        request = ItemRequest(name="New Item", price=100.0)

        item_info = request.as_item_info()
        assert item_info.name == "New Item"
        assert item_info.price == 100.0
        assert item_info.deleted is False

    def test_item_request_as_item_info_sets_deleted_false(self):
        """Test ItemRequest.as_item_info sets deleted=False"""
        request = ItemRequest(name="New", price=10.0)
        item_info = request.as_item_info()

        assert item_info.name == "New"
        assert item_info.price == 10.0
        assert item_info.deleted is False

    def test_patch_item_request_as_patch_item_info_name_only(self):
        """Test PatchItemRequest.as_patch_item_info with name only"""
        request = PatchItemRequest(name="Updated Name")

        patch_info = request.as_patch_item_info()
        assert patch_info.name == "Updated Name"
        assert patch_info.price is None
        assert patch_info.deleted is None

    def test_patch_item_request_as_patch_item_info_price_only(self):
        """Test PatchItemRequest.as_patch_item_info with price only"""
        request = PatchItemRequest(price=75.0)

        patch_info = request.as_patch_item_info()
        assert patch_info.name is None
        assert patch_info.price == 75.0
        assert patch_info.deleted is None

    def test_patch_item_request_as_patch_item_info_both(self):
        """Test PatchItemRequest.as_patch_item_info with both fields"""
        request = PatchItemRequest(name="Updated", price=125.0)

        patch_info = request.as_patch_item_info()
        assert patch_info.name == "Updated"
        assert patch_info.price == 125.0
        assert patch_info.deleted is None

    def test_patch_item_request_with_none_values(self):
        """Test PatchItemRequest with all None values"""
        request = PatchItemRequest()
        patch_info = request.as_patch_item_info()

        assert patch_info.name is None
        assert patch_info.price is None
        assert patch_info.deleted is None

    def test_patch_item_request_extra_field_forbidden(self):
        """Test PatchItemRequest validation with extra field"""
        # This should raise ValidationError due to extra="forbid"
        with pytest.raises(ValidationError):
            PatchItemRequest(name="New", extra_field="forbidden")


class TestCartContracts:
    """Tests for Cart contracts (Pydantic models)"""

    def test_cart_response_from_entity(self):
        """Test CartResponse.from_entity method"""
        entity = CartEntity(
            id=1,
            info=CartInfo(
                items=[CartItemInfo(id=1, name="Item", quantity=2, available=True)],
                price=20.0
            )
        )

        response = CartResponse.from_entity(entity)
        assert response.id == 1
        assert len(response.items) == 1
        assert response.price == 20.0

    def test_cart_response_with_empty_items(self):
        """Test CartResponse.from_entity with empty items list"""
        entity = CartEntity(
            id=1,
            info=CartInfo(items=[], price=0.0)
        )

        response = CartResponse.from_entity(entity)
        assert response.id == 1
        assert response.items == []
        assert response.price == 0.0

    def test_cart_request_as_cart_info(self):
        """Test CartRequest.as_cart_info method"""
        request = CartRequest(
            items=[CartItemInfo(id=1, name="Item", quantity=1, available=True)],
            price=10.0
        )

        cart_info = request.as_cart_info()
        assert len(cart_info.items) == 1
        assert cart_info.price == 10.0

    def test_patch_cart_request_as_patch_cart_info(self):
        """Test PatchCartRequest.as_patch_cart_info method"""
        request = PatchCartRequest(
            items=[CartItemInfo(id=1, name="Item", quantity=2, available=True)]
        )

        patch_info = request.as_patch_cart_info()
        assert patch_info.items is not None
        assert len(patch_info.items) == 1

    def test_patch_cart_request_with_none_items(self):
        """Test PatchCartRequest with None items"""
        request = PatchCartRequest()
        patch_info = request.as_patch_cart_info()

        assert patch_info.items is None

    def test_patch_cart_request_extra_field_forbidden(self):
        """Test PatchCartRequest validation with extra field"""
        # This should raise ValidationError due to extra="forbid"
        with pytest.raises(ValidationError):
            PatchCartRequest(items=[], extra_field="forbidden")
