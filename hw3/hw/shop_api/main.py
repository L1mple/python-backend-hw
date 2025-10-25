from fastapi import FastAPI

from shop_api.cart.routers import router as cart
from shop_api.item.routers  import router as item

from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(title="Shop API")

app.include_router(cart)
app.include_router(item)

# Initialise l'instrumentation
instrumentator = Instrumentator()

# Instrumente l'application et expose le point de terminaison /metrics
instrumentator.instrument(app)
instrumentator.expose(app)

@app.get("/")
async def root():
    return {"message": "API Shop is running"}

