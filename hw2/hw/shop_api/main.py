from fastapi import FastAPI
from routes import router

app = FastAPI(title="Shop API")

app.include_router(router)
