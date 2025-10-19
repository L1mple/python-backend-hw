from fastapi import FastAPI

from rest_example.api.pokemon import router

app = FastAPI(title="Pokemon REST API Example")

app.include_router(router)
