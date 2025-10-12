from fastapi import FastAPI
from shop_api.routers.item import router as item
from shop_api.routers.cart import router as cart
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(item)
app.include_router(cart)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8001)
