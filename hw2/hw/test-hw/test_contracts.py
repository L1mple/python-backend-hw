"""Tests for shop_api.contracts module"""
import pytest
from pydantic import ValidationError
from shop_api.contracts import (
    IdModel,
    ItemRequest,
    ItemPatchRequest,
    ItemModel,
    ListQueryModel,
    CartItemModel,
    CartResponseModel,
)
from shop_api.store.storage import ItemData, CartData, ItemnInCartData


class TestIdModel:
    """Test IdModel"""

    def test_id_model_valid(self):
        """Test valid IdModel creation"""
        model = IdModel(id=1)
        assert model.id == 1

    def test_id_model_dict(self):
        """Test IdModel to dict"""
        model = IdModel(id=42)
        assert model.model_dump() == {"id": 42}


class TestItemRequest:
    """Test ItemRequest"""

    def test_item_request_valid(self):
        """Test valid ItemRequest creation"""
        item = ItemRequest(name="Test Item", price=10.99)
        assert item.name == "Test Item"
        assert item.price == 10.99

    def test_item_request_negative_price(self):
        """Test ItemRequest with negative price should fail"""
        with pytest.raises(ValidationError):
            ItemRequest(name="Test", price=-5.0)

    def test_item_request_zero_price(self):
        """Test ItemRequest with zero price should fail"""
        with pytest.raises(ValidationError):
            ItemRequest(name="Test", price=0.0)

    def test_item_request_missing_name(self):
        """Test ItemRequest without name should fail"""
        with pytest.raises(ValidationError):
            ItemRequest(price=10.0)


class TestItemPatchRequest:
    """Test ItemPatchRequest"""

    def test_item_patch_request_empty(self):
        """Test empty ItemPatchRequest"""
        item = ItemPatchRequest()
        assert item.name is None
        assert item.price is None

    def test_item_patch_request_name_only(self):
        """Test ItemPatchRequest with name only"""
        item = ItemPatchRequest(name="New Name")
        assert item.name == "New Name"
        assert item.price is None

    def test_item_patch_request_price_only(self):
        """Test ItemPatchRequest with price only"""
        item = ItemPatchRequest(price=15.99)
        assert item.name is None
        assert item.price == 15.99

    def test_item_patch_request_both(self):
        """Test ItemPatchRequest with both fields"""
        item = ItemPatchRequest(name="New Name", price=15.99)
        assert item.name == "New Name"
        assert item.price == 15.99

    def test_item_patch_request_negative_price(self):
        """Test ItemPatchRequest with negative price should fail"""
        with pytest.raises(ValidationError):
            ItemPatchRequest(price=-5.0)

    def test_item_patch_request_extra_field(self):
        """Test ItemPatchRequest with extra field should fail"""
        with pytest.raises(ValidationError):
            ItemPatchRequest(name="Test", price=10.0, extra_field="not allowed")


class TestItemModel:
    """Test ItemModel"""

    def test_item_model_valid(self):
        """Test valid ItemModel creation"""
        item = ItemModel(id=1, name="Test", price=10.0, deleted=False)
        assert item.id == 1
        assert item.name == "Test"
        assert item.price == 10.0
        assert item.deleted is False

    def test_item_model_default_deleted(self):
        """Test ItemModel with default deleted value"""
        item = ItemModel(id=1, name="Test", price=10.0)
        assert item.deleted is False

    def test_item_model_from_entity(self):
        """Test ItemModel.from_entity conversion"""
        entity = ItemData(id=5, name="Entity Item", price=25.5, deleted=False)
        model = ItemModel.from_entity(entity)
        assert model.id == 5
        assert model.name == "Entity Item"
        assert model.price == 25.5
        assert model.deleted is False

    def test_item_model_from_entity_deleted(self):
        """Test ItemModel.from_entity with deleted item"""
        entity = ItemData(id=10, name="Deleted Item", price=50.0, deleted=True)
        model = ItemModel.from_entity(entity)
        assert model.id == 10
        assert model.deleted is True


class TestListQueryModel:
    """Test ListQueryModel"""

    def test_list_query_defaults(self):
        """Test ListQueryModel with default values"""
        query = ListQueryModel()
        assert query.offset == 0
        assert query.limit == 10
        assert query.min_price is None
        assert query.max_price is None
        assert query.show_deleted is False
        assert query.min_quantity is None
        assert query.max_quantity is None

    def test_list_query_custom_values(self):
        """Test ListQueryModel with custom values"""
        query = ListQueryModel(
            offset=5,
            limit=20,
            min_price=10.0,
            max_price=100.0,
            show_deleted=True,
            min_quantity=1,
            max_quantity=10,
        )
        assert query.offset == 5
        assert query.limit == 20
        assert query.min_price == 10.0
        assert query.max_price == 100.0
        assert query.show_deleted is True
        assert query.min_quantity == 1
        assert query.max_quantity == 10

    def test_list_query_negative_offset(self):
        """Test ListQueryModel with negative offset should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(offset=-1)

    def test_list_query_zero_limit(self):
        """Test ListQueryModel with zero limit should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(limit=0)

    def test_list_query_negative_limit(self):
        """Test ListQueryModel with negative limit should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(limit=-1)

    def test_list_query_negative_min_price(self):
        """Test ListQueryModel with negative min_price should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(min_price=-10.0)

    def test_list_query_negative_max_price(self):
        """Test ListQueryModel with negative max_price should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(max_price=-5.0)

    def test_list_query_negative_min_quantity(self):
        """Test ListQueryModel with negative min_quantity should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(min_quantity=-1)

    def test_list_query_negative_max_quantity(self):
        """Test ListQueryModel with negative max_quantity should fail"""
        with pytest.raises(ValidationError):
            ListQueryModel(max_quantity=-1)


class TestCartItemModel:
    """Test CartItemModel"""

    def test_cart_item_model_valid(self):
        """Test valid CartItemModel creation"""
        item = CartItemModel(id=1, name="Item", quantity=3, available=True)
        assert item.id == 1
        assert item.name == "Item"
        assert item.quantity == 3
        assert item.available is True


class TestCartResponseModel:
    """Test CartResponseModel"""

    def test_cart_response_model_empty(self):
        """Test CartResponseModel with empty cart"""
        cart = CartResponseModel(id=1, items=[], price=0.0)
        assert cart.id == 1
        assert cart.items == []
        assert cart.price == 0.0

    def test_cart_response_model_with_items(self):
        """Test CartResponseModel with items"""
        items = [
            CartItemModel(id=1, name="Item1", quantity=2, available=True),
            CartItemModel(id=2, name="Item2", quantity=1, available=False),
        ]
        cart = CartResponseModel(id=5, items=items, price=50.0)
        assert cart.id == 5
        assert len(cart.items) == 2
        assert cart.price == 50.0

    def test_cart_response_from_entity_empty(self):
        """Test CartResponseModel.from_entity with empty cart"""
        entity = CartData(id=10, items=[], price=0.0)
        model = CartResponseModel.from_entity(entity)
        assert model.id == 10
        assert model.items == []
        assert model.price == 0.0

    def test_cart_response_from_entity_with_items(self):
        """Test CartResponseModel.from_entity with items"""
        entity = CartData(
            id=20,
            items=[
                ItemnInCartData(id=1, name="Item1", quantity=3, available=True),
                ItemnInCartData(id=2, name="Item2", quantity=1, available=False),
            ],
            price=75.0,
        )
        model = CartResponseModel.from_entity(entity)
        assert model.id == 20
        assert len(model.items) == 2
        assert model.items[0].id == 1
        assert model.items[0].name == "Item1"
        assert model.items[0].quantity == 3
        assert model.items[0].available is True
        assert model.items[1].id == 2
        assert model.items[1].available is False
        assert model.price == 75.0
