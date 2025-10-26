from fastapi import FastAPI
from .store.routers import cart_router, item_router

app = FastAPI(title="Shop API")

app.include_router(cart_router)
app.include_router(item_router)

@app.get("/")
def read_root():
    return {"message": "Shop API is running"}
