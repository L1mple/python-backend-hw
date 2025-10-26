from fastapi import APIRouter

from app.config import get_settings

from .cart import router as router_cart
from .item import router as router_item

router = APIRouter(prefix=get_settings().prefix.v1, tags=["v1"])

router.include_router(router_item)

router.include_router(router_cart)
