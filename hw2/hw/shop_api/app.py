from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .routers.items import router as items_router
from .routers.carts import router as carts_router
from .routers.chat import register_chat

app = FastAPI(title="Shop API")

instrumentator = Instrumentator()
instrumentator.instrument(app)


@app.on_event("startup")
async def _startup_metrics():
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(items_router)
app.include_router(carts_router)

register_chat(app)
