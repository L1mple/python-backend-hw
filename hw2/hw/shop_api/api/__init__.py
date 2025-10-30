from fastapi import APIRouter
from .cart.routes import router as cart_router
from .item.routes import router as item_router

router = APIRouter()

router.include_router(cart_router, prefix="/cart", tags=["cart"])
router.include_router(item_router, prefix="/item", tags=["item"])
