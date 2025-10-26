from fastapi import FastAPI

from .routes import router as api_router

app = FastAPI(title="Shop API"
              )
app.include_router(api_router)