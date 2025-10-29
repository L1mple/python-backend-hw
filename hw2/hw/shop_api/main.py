from fastapi import FastAPI
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from .routes import items_router, carts_router
from .storage import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = storage
    yield


app = FastAPI(title="Shop API", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

app.include_router(items_router)
app.include_router(carts_router)

