import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from http import HTTPStatus

from shop_api.handlers.cart import router
from shop_api.models.item import ItemSchema
from shop_api.models.cart import CartOutSchema


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_data():
    item1 = ItemSchema(name="Test Item", id="item-1", quantity=1, price=10.0)
    item2 = ItemSchema(name="Test Item", id="item-2", quantity=2, price=25.0)
    
    cart1_item = item1.model_copy() 
    cart1 = CartOutSchema(id="cart-123", items=[cart1_item]) 
    
    cart2 = CartOutSchema(
        id="cart-456", 
        items=[
            item1.model_copy(update={"quantity": 3}), 
            item2.model_copy()  
        ]
    )
    
    cart3 = CartOutSchema(id="cart-789", items=[]) 
    
    return {
        "item1": item1,
        "item2": item2,
        "cart1": cart1,
        "cart2": cart2,
        "cart3": cart3,
        "all_carts": [cart1, cart2, cart3]
    }


def test_add_cart(client: TestClient, mocker):
    test_uuid = "new-cart-uuid"
    mocker.patch(
        "shop_api.handlers.cart.uuid.uuid4", 
        return_value=test_uuid
    )
    mock_add_db = mocker.patch("shop_api.handlers.cart.local_data.add_single_cart")

    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    
    expected_data = {"id": test_uuid}
    assert response.json()["id"] == test_uuid
    assert response.headers["Location"] == f"/cart/{test_uuid}"
    
    mock_add_db.assert_called_once_with(cart_data=expected_data)


def test_get_cart_by_id(client: TestClient, mocker, mock_data):
    test_cart = mock_data["cart1"]
    
    mocker.patch(
        "shop_api.handlers.cart.local_data.get_single_cart", 
        return_value=test_cart
    )
    
    response = client.get(f"/cart/{test_cart.id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == test_cart.model_dump()


def test_add_item_to_cart_new_item(client: TestClient, mocker, mock_data):
    cart = mock_data["cart3"]
    item_to_add = mock_data["item1"] 

    mocker.patch("shop_api.handlers.cart.local_data.get_single_cart", return_value=cart)
    
    mocker.patch(
        "shop_api.handlers.cart.local_data.get_all_item_ids_for_cart", 
        return_value=[]
    )
    
    mocker.patch(
        "shop_api.handlers.cart.local_data.get_single_item", 
        return_value=item_to_add
    )
    
    response = client.post(f"/cart/{cart.id}/add/{item_to_add.id}")
    
    assert response.status_code == HTTPStatus.OK
    
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["id"] == item_to_add.id
    assert response_data["items"][0]["quantity"] == 1


def test_add_item_to_cart_existing_item(client: TestClient, mocker, mock_data):
    cart = mock_data["cart1"]
    item_id_to_add = "item-1"

    mocker.patch("shop_api.handlers.cart.local_data.get_single_cart", return_value=cart)
    
    mocker.patch(
        "shop_api.handlers.cart.local_data.get_all_item_ids_for_cart", 
        return_value=[item_id_to_add]
    )
    
    response = client.post(f"/cart/{cart.id}/add/{item_id_to_add}")
    assert response.status_code == HTTPStatus.OK
    
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["id"] == item_id_to_add
    assert response_data["items"][0]["quantity"] == 2


def test_add_item_to_cart_cart_not_found(client: TestClient, mocker):
    mocker.patch("shop_api.handlers.cart.local_data.get_single_cart", return_value=None)
    
    response = client.post("/cart/fake-cart-id/add/fake-item-id")
    
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "wasn't found" in response.json()["detail"]


@pytest.mark.parametrize(
    "params, expected_ids",
    [
        (
            {"offset": 0, "limit": 2}, 
            ["cart-123", "cart-456"]
        ),
        (
            {"offset": 1, "limit": 2}, 
            ["cart-456", "cart-789"]
        ),
        (
            {"offset": 10, "limit": 10}, 
            []
        ),
        (
            {"min_price": 50.0}, 
            ["cart-456"]
        ),
        (
            {"max_price": 50.0}, 
            ["cart-123", "cart-789"]
        ),
        (
            {"min_price": 5.0, "max_price": 20.0}, 
            ["cart-123"]
        ),
        (
            {"min_quantity": 2}, 
            ["cart-456"]
        ),
        (
            {"max_quantity": 2}, 
            ["cart-123", "cart-789"]
        ),
        (
            {"min_quantity": 1, "max_quantity": 1}, 
            ["cart-123"]
        ),
        (
            {"min_price": 5.0, "min_quantity": 2}, 
            ["cart-456"]
        ),
        (
            {"max_price": 90.0, "max_quantity": 1},
            ["cart-123", "cart-789"]
        ),
        (
            {"min_price": 1000.0}, 
            []
        ),
        (
            {}, 
            ["cart-123", "cart-456", "cart-789"] 
        ),
    ],
)
def test_get_all_carts_filtering(
    client: TestClient, mocker, mock_data, params, expected_ids
):
    mocker.patch(
        "shop_api.handlers.cart.local_data.get_all_carts", 
        return_value=mock_data["all_carts"]
    )
    
    response = client.get("/cart", params=params)
    
    assert response.status_code == HTTPStatus.OK
    
    response_data = response.json()
    response_ids = [cart["id"] for cart in response_data]
    
    assert response_ids == expected_ids