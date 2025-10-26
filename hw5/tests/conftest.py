import pytest
from shop_api.storage import memory

class DummyLock:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture(autouse=True)
def patch_lock(monkeypatch):
    monkeypatch.setattr(memory, "_lock", DummyLock())

@pytest.fixture(autouse=True)
def reset_memory():
    memory._carts.clear()
    memory._items.clear()
    memory._next_cart_id = 1
    memory._next_item_id = 1
