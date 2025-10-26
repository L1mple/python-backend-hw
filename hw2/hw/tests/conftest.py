import pytest
from fastapi.testclient import TestClient

from hw2.hw.shop_api.main import app

from hw2.hw.shop_api.store import queries as queries_module


@pytest.fixture(autouse=True)
def clear_storage_before_each_test(monkeypatch):
    fresh_items_db = {}
    fresh_carts_db = {}

    monkeypatch.setattr(queries_module, "_data_items", fresh_items_db)
    monkeypatch.setattr(queries_module, "_data_carts", fresh_carts_db)

    monkeypatch.setattr(queries_module, "_id_generator", queries_module.int_id_generator())


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
