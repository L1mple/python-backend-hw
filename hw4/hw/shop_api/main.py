from fastapi import FastAPI
from hw4.hw.shop_api.store.routers import cart_router, item_router

app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
