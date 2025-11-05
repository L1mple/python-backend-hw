from fastapi import FastAPI
from .routers import items
from .routers import carts
from . import monitoring
from .db import init_db

app = FastAPI(title="Shop API")
app.include_router(items.router)
app.include_router(carts.router)


@app.on_event("startup")
async def on_startup():
    await init_db()

# setup prometheus metrics endpoint and middleware
monitoring.setup_metrics(app)
