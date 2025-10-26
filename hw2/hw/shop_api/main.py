from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from shop_api.cart_routes import cart_router
from shop_api.item_routes import item_router
from shop_api.database import init_db

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

# Initialize database tables
init_db()

app.include_router(cart_router)
app.include_router(item_router)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

