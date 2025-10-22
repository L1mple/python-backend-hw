from fastapi import FastAPI
from .cart_routes import cart_router
from .item_routes import item_router
app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

