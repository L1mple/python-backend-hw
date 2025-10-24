from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from shop_api.routers import items, carts
from shop_api.database import Base, engine
from shop_api import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

app.include_router(items.router)
app.include_router(carts.router)

@app.get("/")
async def root():
    return {"message": "Shop API with SQLite"}