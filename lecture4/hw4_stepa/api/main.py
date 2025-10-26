from fastapi import FastAPI
from .routes import basket_router, product_router

app = FastAPI(
    title="Stepa Shop API",
    description="API for managing products and baskets with transaction isolation examples",
    version="1.0.0"
)

app.include_router(basket_router)
app.include_router(product_router)

@app.get("/")
def api_root():
    return {"message": "Stepa Shop API is operational"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "stepa_shop_api"}
