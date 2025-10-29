from fastapi import FastAPI

from . import cart_routes, chat_routes, item_routes

app = FastAPI(title="Shop API")

app.include_router(item_routes.router)
app.include_router(cart_routes.router)
app.include_router(chat_routes.router)
