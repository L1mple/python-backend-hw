from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .api.cart import router as cart_router
from .api.item import router as item_router
from .store.database import create_tables, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup and cleanup on shutdown"""
    # Startup: Create database tables
    print("🚀 Initializing database...")
    create_tables()
    print("✓ Database initialized successfully")

    yield

    # Shutdown: Close database connections
    print("🔄 Closing database connections...")
    engine.dispose()
    print("✓ Database connections closed")


app = FastAPI(title="Shop API", lifespan=lifespan)
app.include_router(cart_router)
app.include_router(item_router)

Instrumentator().instrument(app).expose(app)
