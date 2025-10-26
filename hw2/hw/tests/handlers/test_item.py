import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from http import HTTPStatus

from shop_api.handlers.item import router
from shop_api.models.item import ItemSchema


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_data():
    item1 = ItemSchema(id="item-1", name="Apple", price=10.0, quantity=5)
    item2 = ItemSchema(id="item-2", name="Banana", price=100.0, quantity=1)
    item3_deleted = ItemSchema(id="item-3", name="Cherry", price=50.0, quantity=10, deleted=True)
    return {
        "item1": item1,
        "item2": item2,
        "item3_deleted": item3_deleted,
        "all_items": [item1, item2, item3_deleted]
    }

def test_add_item(client: TestClient, mocker):
    test_uuid = "new-item-uuid"

    item_create_data = {"name": "Test Item", "price": 9.99, "quantity": 1}
    
    mocker.patch("shop_api.handlers.item.uuid.uuid4", return_value=test_uuid)
    mock_add_db = mocker.patch("shop_api.handlers.item.local_data.add_single_item")
    
    response = client.post("/item", json=item_create_data)
    
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers["Location"] == f"/item/{test_uuid}"

    data_sent_to_db = {
        "id": test_uuid,
        "name": "Test Item",
        "price": 9.99
    }

    data_returned_to_client = {
        "id": test_uuid,
        "name": "Test Item",
        "price": 9.99,
        "quantity": 1,     
        "deleted": False  
    }

    assert response.json() == data_returned_to_client
    
    mock_add_db.assert_called_once_with(
        item_id=test_uuid,
        item_data=data_sent_to_db
    )

def test_get_item_by_id_success(client: TestClient, mocker, mock_data):
    test_item = mock_data["item1"]
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=test_item)
    
    response = client.get(f"/item/{test_item.id}")
    
    assert response.status_code == HTTPStatus.OK
    assert response.json() == test_item.model_dump()

def test_get_item_by_id_deleted(client: TestClient, mocker, mock_data):
    deleted_item = mock_data["item3_deleted"]
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=deleted_item)
    
    response = client.get(f"/item/{deleted_item.id}")
    
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "was deleted" in response.json()["detail"]

@pytest.mark.parametrize(
    "params, expected_ids",
    [
        ({}, ["item-1", "item-2"]),
        ({"show_deleted": True}, ["item-1", "item-2", "item-3"]),
        ({"limit": 1}, ["item-1"]),
        ({"offset": 1}, ["item-2"]),
        ({"offset": 1, "limit": 1, "show_deleted": True}, ["item-2"]),
        ({"min_price": 20.0}, ["item-2"]),
        ({"min_price": 20.0, "show_deleted": False}, ["item-2"]),
        ({"max_price": 20.0}, ["item-1"]),
        ({"min_price": 5.0, "max_price": 60.0, "show_deleted": True}, ["item-1", "item-3"]),
        ({"min_price": 1000.0}, []),
    ],
)
def test_get_all_items(client: TestClient, mocker, mock_data, params, expected_ids):
    mocker.patch("shop_api.handlers.item.local_data.get_all_items", return_value=mock_data["all_items"])
    
    response = client.get("/item", params=params)
    
    assert response.status_code == HTTPStatus.OK
    response_ids = [item["id"] for item in response.json()]
    assert response_ids == expected_ids

def test_change_item(client: TestClient, mocker, mock_data):
    existing_item = mock_data["item1"]
    
    updated_item_data = {
        "id": existing_item.id,
        "name": "New Apple",
        "price": 15.0,
        "quantity": 2,
        "deleted": False
    }
    
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=existing_item)
    mock_add_db = mocker.patch("shop_api.handlers.item.local_data.add_single_item")
    
    response = client.put(f"/item/{existing_item.id}", json=updated_item_data)
    
    assert response.status_code == HTTPStatus.OK
    assert response.json() == updated_item_data
    
    updated_model = ItemSchema(**updated_item_data)
    mock_add_db.assert_called_once_with(
        item_id=existing_item.id,
        item_data=updated_model
    )

def test_change_item_not_found(client: TestClient, mocker):
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=None)
    
    invalid_data = {"id": "fake-id", "name": "Fake", "price": 1, "quantity": 1, "deleted": False}
    response = client.put("/item/fake-id", json=invalid_data)
    
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_change_item_fields(client: TestClient, mocker, mock_data):
    old_item = mock_data["item1"].model_copy()
    patch_data = {"name": "Gala Apple", "quantity": 50}
    
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=old_item)
    mock_add_db = mocker.patch("shop_api.handlers.item.local_data.add_single_item")
    
    response = client.patch(f"/item/{old_item.id}", json=patch_data)
    
    assert response.status_code == HTTPStatus.OK
    
    expected_item = old_item.model_copy(update=patch_data)
    assert response.json() == expected_item.model_dump()
    
    mock_add_db.assert_called_once_with(
        item_id=old_item.id,
        item_data=expected_item
    )

def test_change_item_fields_not_found(client: TestClient, mocker):
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=None)
    response = client.patch("/item/fake-id", json={"name": "test"})
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_change_item_fields_deleted(client: TestClient, mocker, mock_data):
    deleted_item = mock_data["item3_deleted"]
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=deleted_item)
    
    response = client.patch(f"/item/{deleted_item.id}", json={"name": "test"})
    
    assert response.status_code == HTTPStatus.NOT_MODIFIED

def test_delete_item(client: TestClient, mocker, mock_data):
    item_to_delete = mock_data["item1"]
    
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=item_to_delete)
    mock_delete_db = mocker.patch("shop_api.handlers.item.local_data.delete_item")
    
    response = client.delete(f"/item/{item_to_delete.id}")
    
    assert response.status_code == HTTPStatus.OK
    assert response.json() == item_to_delete.model_dump()
    
    mock_delete_db.assert_called_once_with(item_id=item_to_delete.id)

def test_delete_item_not_found(client: TestClient, mocker):
    mocker.patch("shop_api.handlers.item.local_data.get_single_item", return_value=None)
    response = client.delete("/item/fake-id")
    assert response.status_code == HTTPStatus.NOT_FOUND