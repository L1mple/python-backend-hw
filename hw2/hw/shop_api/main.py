from fastapi import FastAPI
from .routers import items, carts
from .factory import ItemCreate
from .database import db


app = FastAPI(title="Shop API")

app.include_router(items.router)
app.include_router(carts.router)
