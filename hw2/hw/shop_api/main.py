from contextlib import asynccontextmanager
from fastapi import FastAPI
from shop_api.routers.item import router as item
from shop_api.routers.cart import router as cart
from prometheus_fastapi_instrumentator import Instrumentator
from shop_api.core.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Shop API", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

app.include_router(item)
app.include_router(cart)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8001)
