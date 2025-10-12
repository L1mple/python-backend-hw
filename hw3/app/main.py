from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.pokemon import router as pokemon_router

app = FastAPI(title="Pokemon REST API Example")

app.include_router(pokemon_router)

instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app)
