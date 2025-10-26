from fastapi import FastAPI

from src.routers import item_router, cart_router



pg_app = FastAPI()

pg_app.include_router(
    router=cart_router,
    prefix="/carts",
    tags=["Cart"]
)
pg_app.include_router(
    router=item_router,
    prefix="/items",
    tags=["Items"]
)