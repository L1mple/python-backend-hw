from fastapi import APIRouter

from .cartt import router as cart_router
from .item import router as item_router

router = APIRouter()
router.include_router(item_router, prefix="/item", tags=["item"])
router.include_router(cart_router, prefix="/cart", tags=["cart"])