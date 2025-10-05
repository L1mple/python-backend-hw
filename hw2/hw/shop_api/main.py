from fastapi import FastAPI

from hw2.hw.shop_api.routes import cartRouter, itemRouter

app = FastAPI(title="Shop API")

app.include_router(cartRouter)
app.include_router(itemRouter)
