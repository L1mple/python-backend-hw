from fastapi import FastAPI, Query, HTTPException, Response
from .routes.item import router as item_router
from .routes.cart import router as cart_router

app = FastAPI(title="Shop API")

app.include_router(item_router)
app.include_router(cart_router)
