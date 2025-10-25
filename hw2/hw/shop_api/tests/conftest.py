import pytest



@pytest.fixture
def sample_item_data():
    return {
        "name": "Test Item",
        "price": 100.0,
        "deleted": False
    }

