from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .routers import items, carts
from .database import Base, engine
from . import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

app.include_router(items.router)
app.include_router(carts.router)

@app.get("/")
async def root():
    return {"message": "Shop API with SQLite"}