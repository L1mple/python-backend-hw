from fastapi import FastAPI
from .routers import items
from .routers import carts
from . import monitoring

app = FastAPI(title="Shop API")
app.include_router(items.router)
app.include_router(carts.router)

# setup prometheus metrics endpoint and middleware
monitoring.setup_metrics(app)
