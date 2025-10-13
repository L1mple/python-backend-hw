from fastapi import FastAPI

from api.cart.routes import router as cart_router
from api.item.routes import router as item_router
from api.metrics.routes import router as metrics_router

app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
app.include_router(metrics_router)
