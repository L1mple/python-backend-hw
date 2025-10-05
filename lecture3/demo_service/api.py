from http import HTTPStatus
from typing import Annotated
import random

from fastapi import FastAPI, HTTPException, Query
from prometheus_fastapi_instrumentator import Instrumentator

from demo_service import store
from demo_service.contracts import UserRequest, UserResource

app = FastAPI(title="Demo User API")
Instrumentator().instrument(app).expose(app)


def maybe_raise_random_error():
    if random.random() < 0.1:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Random error occurred"
        )


@app.post(
    "/create-user",
    response_model=UserResource,
    status_code=HTTPStatus.CREATED,
)
async def create_user(body: UserRequest) -> UserResource:
    maybe_raise_random_error()
    return store.insert(body)


@app.post("/get-user")
async def get_user(id: Annotated[int, Query()]) -> UserResource:
    maybe_raise_random_error()

    resource = store.select(id)

    if not resource:
        raise HTTPException(HTTPStatus.NOT_FOUND)

    return resource
