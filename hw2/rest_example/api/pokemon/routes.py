from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from hw2.rest_example import store

from .contracts import (
    PatchPokemonRequest,
    PokemonRequest,
    PokemonResponse,
)

router = APIRouter(prefix="/pokemon")


@router.get("/")
async def get_pokemon_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
) -> list[PokemonResponse]:
    return [PokemonResponse.from_entity(e) for e in store.get_many(offset, limit)]


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested pokemon",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested pokemon as one was not found",
        },
    },
)
async def get_pokemon_by_id(id: int) -> PokemonResponse:
    entity = store.get_one(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /pokemon/{id} was not found",
        )

    return PokemonResponse.from_entity(entity)


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_pokemon(info: PokemonRequest, response: Response) -> PokemonResponse:
    entity = store.add(info.as_pokemon_info())

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/pokemon/{entity.id}"

    return PokemonResponse.from_entity(entity)


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched pokemon",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify pokemon as one was not found",
        },
    },
)
async def patch_pokemon(id: int, info: PatchPokemonRequest) -> PokemonResponse:
    entity = store.patch(id, info.as_patch_pokemon_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /pokemon/{id} was not found",
        )

    return PokemonResponse.from_entity(entity)


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted pokemon",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify pokemon as one was not found",
        },
    }
)
async def put_pokemon(
    id: int,
    info: PokemonRequest,
    upsert: Annotated[bool, Query()] = False,
) -> PokemonResponse:
    entity = (
        store.upsert(id, info.as_pokemon_info())
        if upsert
        else store.update(id, info.as_pokemon_info())
    )

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /pokemon/{id} was not found",
        )

    return PokemonResponse.from_entity(entity)


@router.delete("/{id}")
async def delete_pokemon(id: int) -> Response:
    store.delete(id)
    return Response("")
