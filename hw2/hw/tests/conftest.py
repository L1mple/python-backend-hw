import pytest
from fastapi.testclient import TestClient

from shop_api.main import app
from shop_api.store import queries as queries_module


@pytest.fixture(autouse=True)
def clear_storage():
    queries_module._data_items.clear()
    queries_module._data_carts.clear()
    queries_module._id_generator = queries_module.int_id_generator()
    yield


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)