from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from app.api import router as router_api
from app.config import get_settings
from app.core.mongo import client as mongo_client
from app.core.mongo import get_mongo
from app.utils.mongo import init_mongo_collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Launch MongoDB ---
    mongo = await get_mongo()
    mongodb = mongo.mongo
    await init_mongo_collections()
    logger.info("MongoDB client ready")
    # --- Yield to FastAPI ---
    try:
        logger.success("Application is running")
        yield
    finally:
        # --- Close MongoDB ---
        mongo_client.close()
        logger.info("MongoDB client closed")
        logger.success("Application is stopped")


app = FastAPI(lifespan=lifespan)

app.include_router(router_api)


if __name__ == "__main__":
    uvicorn.run(app, host=get_settings().app.host, port=get_settings().app.port)