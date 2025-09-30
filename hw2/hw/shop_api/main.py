from fastapi import FastAPI

from hw2.hw.shop_api.routes import router

app = FastAPI(title="Shop API")

app.include_router(router)
