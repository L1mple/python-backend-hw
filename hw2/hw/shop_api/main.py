from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
import pydantic
import fastapi
import sys
import platform
import datetime
from shop_api.handlers import router
from shop_api.storage.psql_sqlalchemy import init_engine, create_schema


def lifespan(app):
    init_engine()
    create_schema()
    print("Database initialized", "Shema created")
    yield


VERSION = "1.0.0"
AUTHOR = "Neimess"
BUILD_DATE = datetime.datetime.now().isoformat()


print("=" * 60)
print("Task API started")
print(f"Version: {VERSION}")
print(f"Build date: {BUILD_DATE}")
print(f"Author: {AUTHOR}")
print(f"Python: {sys.version.split()[0]}")
print(f"Platform: {platform.system()} {platform.release()}")
print(f"FastAPI: {fastapi.__version__}")
print(f"Pydantic: {pydantic.__version__}")
print("=" * 60)

app = FastAPI(title="Shop API", lifespan=lifespan)
app.include_router(router)


Instrumentator().instrument(app).expose(app)
