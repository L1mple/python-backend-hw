from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .routers.items import router as items_router
from .routers.carts import router as carts_router
from .routers.chat import register_chat

from .db import init_db

app = FastAPI(title="Shop API")
init_db()
instrumentator = Instrumentator()
instrumentator.instrument(app)


@app.on_event("startup")
async def _startup():
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    init_db()
    
app.include_router(items_router)
app.include_router(carts_router)
register_chat(app)
