from fastapi import FastAPI

from .routes import items_router, carts_router

app = FastAPI(title="Shop API")

app.include_router(items_router)
app.include_router(carts_router)
