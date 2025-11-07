from fastapi import FastAPI
from src.routes.item import app as item_router
from src.routes.cart import app as cart_router

app = FastAPI(title="HW4 shop_api")

app.include_router(item_router)
app.include_router(cart_router)