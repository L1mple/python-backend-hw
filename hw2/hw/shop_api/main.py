from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from hw2.hw.shop_api.routes import cartRouter, itemRouter

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(cartRouter)
app.include_router(itemRouter)
