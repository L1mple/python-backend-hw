from fastapi import FastAPI

from shop_api.api.cart.routes import router as cart_router
from shop_api.api.item.routes import router as item_router

app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
