from fastapi import FastAPI

from shop_api.api.cart.routes import router as cart_router
from shop_api.api.item.routes import router as item_router
from shop_api.api.metrics.routes import router as metrics_router
from shop_api.store.database import init_db

app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
app.include_router(metrics_router)


@app.on_event("startup")
def startup() -> None:
    init_db()
