from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from shop_api.api.item import item_router
from shop_api.api.cart import cart_router

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


app.include_router(item_router)
app.include_router(cart_router)