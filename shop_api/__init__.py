# Package shim to expose hw2.hw.shop_api as top-level package `shop_api` for tests
from .main import app  # noqa: F401

