from fastapi.testclient import TestClient
from shop_api import main

client = TestClient(main.app)


def test_app_exists():
    assert main.app is not None


def test_routers_included():
    route_paths = [route.path for route in main.app.routes]
    assert "/item/" in route_paths or any(p.startswith("/item") for p in route_paths)
    assert "/cart/" in route_paths or any(p.startswith("/cart") for p in route_paths)
    assert "/chat/" in route_paths or any(p.startswith("/chat") for p in route_paths)


def test_main_app_root_status():
    response = client.get("/")
    assert response.status_code in (404, 200)
