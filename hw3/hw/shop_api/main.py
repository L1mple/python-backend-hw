from fastapi import FastAPI
from shop_api.store.routers import cart_router, item_router
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)

Instrumentator().instrument(app).expose(app)

