from __future__ import annotations

from fastapi import APIRouter, Depends, status

from ..dependencies import get_item_service
from ..models import (
    ItemCreateRequest,
    ItemCreateResponse,
    ItemListQuery,
    ItemPatchRequest,
    ItemResponse,
    ItemUpdateRequest,
)
from ..services import ItemService

router = APIRouter()


@router.post(
    "",
    response_model=ItemCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    request: ItemCreateRequest,
    item_service: ItemService = Depends(get_item_service),
) -> ItemCreateResponse:
    return item_service.create(request)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    return item_service.get(item_id)


@router.get("", response_model=list[ItemResponse])
def list_items(
    query: ItemListQuery = Depends(),
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    return item_service.list(query)


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    request: ItemUpdateRequest,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    return item_service.update(item_id, request)


@router.patch("/{item_id}", response_model=ItemResponse)
def patch_item(
    item_id: int,
    request: ItemPatchRequest,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    return item_service.patch(item_id, request)


@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service),
) -> None:
    item_service.delete(item_id)