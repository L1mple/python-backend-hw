from fastapi import FastAPI

from hw2.hw.shop_api.api import cart, item

app = FastAPI(title="Shop API")

app.include_router(cart.router)
app.include_router(item.router)
