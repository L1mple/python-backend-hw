import pytest
import pytest_cov
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shop_api.main import app, Base, ItemDB, CartDB, CartItemDB, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(setup_database):
    return TestClient(app)

@pytest.fixture
def sample_item():
    return {"name": "Test Item", "price": 100.0}

@pytest.fixture
def sample_item_update():
    return {"name": "Updated Item", "price": 150.0, "deleted": False}

@pytest.fixture
def sample_item_patch():
    return {"name": "Patched Item", "price": 200.0}

def test_create_item(client, sample_item):
    response = client.post("/item", json=sample_item)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_item["name"]
    assert data["price"] == sample_item["price"]
    assert data["deleted"] == False
    assert "id" in data

def test_create_item_invalid_data(client):
    response = client.post("/item", json={"name": "Test"})
    assert response.status_code == 422

def test_get_item(client, sample_item):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_item["name"]
    assert data["price"] == sample_item["price"]

def test_get_item_not_found(client):
    response = client.get("/item/999")
    assert response.status_code == 404

def test_get_item_deleted(client, sample_item):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    client.delete(f"/item/{item_id}")
    
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 404

def test_get_item_list(client, sample_item):
    client.post("/item", json=sample_item)
    client.post("/item", json={"name": "Item 2", "price": 200.0})
    
    response = client.get("/item")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_get_item_list_with_filters(client, sample_item):
    client.post("/item", json=sample_item)
    client.post("/item", json={"name": "Item 2", "price": 200.0})
    
    response = client.get("/item?min_price=150")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price"] == 200.0

def test_get_item_list_with_limit(client, sample_item):
    client.post("/item", json=sample_item)
    client.post("/item", json={"name": "Item 2", "price": 200.0})
    
    response = client.get("/item?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_get_item_list_show_deleted(client, sample_item):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    client.delete(f"/item/{item_id}")
    
    response = client.get("/item?show_deleted=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["deleted"] == True

def test_put_item(client, sample_item, sample_item_update):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    response = client.put(f"/item/{item_id}", json=sample_item_update)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_item_update["name"]
    assert data["price"] == sample_item_update["price"]

def test_put_item_not_found(client, sample_item_update):
    response = client.put("/item/999", json=sample_item_update)
    assert response.status_code == 404

def test_patch_item(client, sample_item, sample_item_patch):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    response = client.patch(f"/item/{item_id}", json=sample_item_patch)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_item_patch["name"]
    assert data["price"] == sample_item_patch["price"]

def test_patch_item_not_found(client, sample_item_patch):
    response = client.patch("/item/999", json=sample_item_patch)
    assert response.status_code == 404

def test_patch_item_deleted(client, sample_item, sample_item_patch):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    client.delete(f"/item/{item_id}")
    
    response = client.patch(f"/item/{item_id}", json=sample_item_patch)
    assert response.status_code == 304

def test_delete_item(client, sample_item):
    create_response = client.post("/item", json=sample_item)
    item_id = create_response.json()["id"]
    
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200
    
    get_response = client.get(f"/item/{item_id}")
    assert get_response.status_code == 404

def test_delete_item_not_found(client):
    response = client.delete("/item/999")
    assert response.status_code == 404

def test_create_cart(client):
    response = client.post("/cart")
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["items"] == []
    assert data["price"] == 0.0

def test_get_cart(client):
    create_response = client.post("/cart")
    cart_id = create_response.json()["id"]
    
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id

def test_get_cart_not_found(client):
    response = client.get("/cart/999")
    assert response.status_code == 404

def test_get_cart_list(client):
    client.post("/cart")
    client.post("/cart")
    
    response = client.get("/cart")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_get_cart_list_with_filters(client):
    cart1_response = client.post("/cart")
    cart1_id = cart1_response.json()["id"]
    
    item_response = client.post("/item", json={"name": "Test Item", "price": 100.0})
    item_id = item_response.json()["id"]
    
    client.post(f"/cart/{cart1_id}/add/{item_id}")
    
    response = client.get("/cart?min_price=50")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_add_item_to_cart(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == item_id
    assert data["items"][0]["quantity"] == 1
    assert data["price"] == sample_item["price"]

def test_add_item_to_cart_multiple_times(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    client.post(f"/cart/{cart_id}/add/{item_id}")
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["price"] == sample_item["price"] * 2

def test_add_item_to_cart_cart_not_found(client, sample_item):
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    response = client.post(f"/cart/999/add/{item_id}")
    assert response.status_code == 404

def test_add_item_to_cart_item_not_found(client):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/999")
    assert response.status_code == 404

def test_add_deleted_item_to_cart(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    client.delete(f"/item/{item_id}")
    
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 404

def test_cart_price_calculation(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item1_response = client.post("/item", json=sample_item)
    item1_id = item1_response.json()["id"]
    
    item2_response = client.post("/item", json={"name": "Item 2", "price": 200.0})
    item2_id = item2_response.json()["id"]
    
    client.post(f"/cart/{cart_id}/add/{item1_id}")
    client.post(f"/cart/{cart_id}/add/{item2_id}")
    
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 300.0

def test_cart_item_availability(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    client.post(f"/cart/{cart_id}/add/{item_id}")
    
    client.delete(f"/item/{item_id}")
    
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["available"] == False

def test_cart_list_quantity_filters(client, sample_item):
    cart1_response = client.post("/cart")
    cart1_id = cart1_response.json()["id"]
    
    cart2_response = client.post("/cart")
    cart2_id = cart2_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    client.post(f"/cart/{cart1_id}/add/{item_id}")
    client.post(f"/cart/{cart1_id}/add/{item_id}")
    
    client.post(f"/cart/{cart2_id}/add/{item_id}")
    
    response = client.get("/cart?min_quantity=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_cart_list_max_quantity_filters(client, sample_item):
    cart1_response = client.post("/cart")
    cart1_id = cart1_response.json()["id"]
    
    cart2_response = client.post("/cart")
    cart2_id = cart2_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    client.post(f"/cart/{cart1_id}/add/{item_id}")
    client.post(f"/cart/{cart1_id}/add/{item_id}")
    
    client.post(f"/cart/{cart2_id}/add/{item_id}")
    
    response = client.get("/cart?max_quantity=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_item_validation_negative_price(client):
    response = client.post("/item", json={"name": "Test", "price": -100.0})
    assert response.status_code == 422

def test_item_validation_empty_name(client):
    response = client.post("/item", json={"name": "", "price": 100.0})
    assert response.status_code == 422

def test_item_validation_missing_fields(client):
    response = client.post("/item", json={"name": "Test"})
    assert response.status_code == 422

def test_cart_offset_limit(client):
    for i in range(5):
        client.post("/cart")
    
    response = client.get("/cart?offset=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_item_offset_limit(client, sample_item):
    for i in range(5):
        client.post("/item", json={"name": f"Item {i}", "price": 100.0 + i})
    
    response = client.get("/item?offset=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_cart_item_quantity_increase(client, sample_item):
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    item_response = client.post("/item", json=sample_item)
    item_id = item_response.json()["id"]
    
    for _ in range(3):
        client.post(f"/cart/{cart_id}/add/{item_id}")
    
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["quantity"] == 3
    assert data["price"] == sample_item["price"] * 3
