from fastapi import FastAPI
from shop_api.routers import items, carts


app = FastAPI(title="Shop API")

app.include_router(items.router)
app.include_router(carts.router)