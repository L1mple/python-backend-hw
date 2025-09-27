from fastapi import FastAPI
from shop_api.routers.item import router as item
from shop_api.routers.cart import router as cart
from shop_api.routers.chat import router as chat

app = FastAPI(title="Shop API")

app.include_router(item)
app.include_router(cart)

app.include_router(chat)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8001)
