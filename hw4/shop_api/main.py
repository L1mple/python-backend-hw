from fastapi import FastAPI
from shop_api.api import cart, item
from shop_api.database import engine
from shop_api.store import models


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API")

app.include_router(cart.router)
app.include_router(item.router)
