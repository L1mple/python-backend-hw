from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator

from db.utils import create_tables
from shop_service.routers.item import router as item_router
from shop_service.routers.cart import router as cart_router

create_tables()
app = FastAPI(title="Shop API")

app.include_router(item_router)
app.include_router(cart_router)

Instrumentator().instrument(app).expose(app)
