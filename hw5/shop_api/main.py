from fastapi import FastAPI
from shop_api.routers import items, carts, chat


app = FastAPI(title="Shop API")

app.include_router(items.router)
app.include_router(carts.router)
app.include_router(chat.router)