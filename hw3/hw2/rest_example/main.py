from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from hw2.rest_example.api.pokemon import router

app = FastAPI(title="Pokemon REST API Example")

app.include_router(router)

instrumentator = Instrumentator(excluded_handlers=["/metrics"])

instrumentator.instrument(app)
instrumentator.expose(app, include_in_schema=True, should_gzip=True)