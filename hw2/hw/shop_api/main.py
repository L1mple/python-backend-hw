from contextlib import asynccontextmanager

from fastapi import FastAPI
# from prometheus_fastapi_instrumentator import Instrumentator

from .database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Shop API", lifespan=lifespan)
# Instrumentator().instrument(app).expose(app)

app.include_router(router)
