from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .routes import items_router, carts_router

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(items_router)
app.include_router(carts_router)


