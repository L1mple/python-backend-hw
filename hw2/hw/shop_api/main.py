from fastapi import FastAPI
from shop_api.handlers.cart import router as cart_router
from shop_api.handlers.item import router as item_router


app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
