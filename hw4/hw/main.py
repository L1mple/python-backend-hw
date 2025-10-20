from fastapi import FastAPI

from shop_api.cart.routers import router as cart
from shop_api.item.routers  import router as item

app = FastAPI(title="Shop API")

app.include_router(cart)
app.include_router(item)

@app.get("/")
async def root():
    return {"message": "API Shop is running"}