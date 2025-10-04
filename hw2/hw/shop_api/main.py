from fastapi import FastAPI

from .shop.routes.item import router as items_router
from .shop.routes.cart import router as cart_router


app = FastAPI(title="Shop API")

app.include_router(items_router)
app.include_router(cart_router)
