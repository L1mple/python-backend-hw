from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from shop_api.core.schemas import ItemOut, ItemCreate, ItemPut, ItemPatch
from shop_api.core import storage

router = APIRouter(prefix="/item", tags=["items"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
async def create_item(body: ItemCreate) -> ItemOut:
    """
    POST /item - добавление нового товара
    """
    return await storage.create_item(body)


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int) -> ItemOut:
    """
    GET /item/{id} - получение товара по id
    """
    return await storage.get_item_or_404(item_id)


@router.get("", response_model=List[ItemOut])
async def list_items(
    offset: int = Query(0, ge=0, description="Смещение (offset)"),
    limit: int = Query(10, gt=0, description="Количество (limit)"),
    min_price: Optional[float] = Query(None, ge=0, description="Мин. цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Макс. цена"),
    show_deleted: bool = Query(False, description="Показывать ли удалённые"),
) -> List[ItemOut]:
    """
    GET /item - получение списка товаров с фильтрами и пагинацией
    """
    return await storage.list_items(offset=offset, limit=limit, min_price=min_price, max_price=max_price, show_deleted=show_deleted)


@router.put("/{item_id}", response_model=ItemOut)
async def put_item(item_id: int, body: ItemPut) -> ItemOut:
    """
    PUT /item/{id} - замена товара по id (создание запрещено)
    """
    return await storage.put_item(item_id, body)


@router.patch("/{item_id}", response_model=ItemOut)
async def patch_item(item_id: int, body: ItemPatch):
    """
    PATCH /item/{id} - частичное обновление (разрешено менять всё кроме deleted)
    Если товар удалён — 304 Not Modified.
    """
    try:
        return await storage.patch_item(item_id, body)
    except HTTPException as e:
        if e.status_code == status.HTTP_304_NOT_MODIFIED:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)
        raise


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    """
    DELETE /item/{id} - мягкое удаление (deleted=True), идемпотентно
    """
    return await storage.delete_item(item_id)
