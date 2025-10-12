from fastapi import APIRouter

from .cart import router as cart_router
from .item import router as item_router
from .chat import router as chat_router

router = APIRouter()

router.include_router(item_router)
router.include_router(cart_router)
router.include_router(chat_router)
