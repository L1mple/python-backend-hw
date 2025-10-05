from fastapi import FastAPI

from shop_api.api.item import item_router
from shop_api.api.cart import cart_router

app = FastAPI(title="Shop API")


app.include_router(item_router)
app.include_router(cart_router)