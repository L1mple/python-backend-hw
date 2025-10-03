from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from shop_api.core.schemas import ItemOut, ItemCreate, ItemPut, ItemPatch
from shop_api.core.storage import _items, _items_lock, get_item_or_404, new_item_id

router = APIRouter(prefix="/item", tags=["items"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
def create_item(body: ItemCreate) -> ItemOut:
    """
    POST /item - добавление нового товара
    """
    item_id = new_item_id()
    obj = ItemOut(id=item_id, name=body.name, price=body.price, deleted=False)
    with _items_lock:
        _items[item_id] = obj
    return obj


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int) -> ItemOut:
    """
    GET /item/{id} - получение товара по id
    """
    return get_item_or_404(item_id)


@router.get("", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0, description="Смещение (offset)"),
    limit: int = Query(10, gt=0, description="Количество (limit)"),
    min_price: Optional[float] = Query(None, ge=0, description="Мин. цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Макс. цена"),
    show_deleted: bool = Query(False, description="Показывать ли удалённые"),
) -> List[ItemOut]:
    """
    GET /item - получение списка товаров с фильтрами и пагинацией
    """
    with _items_lock:
        items = list(_items.values())

    if not show_deleted:
        items = [i for i in items if not i.deleted]
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]

    return items[offset : offset + limit]


@router.put("/{item_id}", response_model=ItemOut)
def put_item(item_id: int, body: ItemPut) -> ItemOut:
    """
    PUT /item/{id} - замена товара по id (создание запрещено)
    """
    with _items_lock:
        existing = _items.get(item_id)
        if existing is None or existing.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        existing.name = body.name
        existing.price = body.price
        return existing


@router.patch("/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, body: ItemPatch):
    """
    PATCH /item/{id} - частичное обновление (разрешено менять всё кроме deleted)
    Если товар удалён — 304 Not Modified.
    """
    with _items_lock:
        existing = _items.get(item_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        if existing.deleted:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)

        if body.name is not None:
            existing.name = body.name
        if body.price is not None:
            if body.price < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid price",
                )
            existing.price = body.price

        return existing


@router.delete("/{item_id}")
def delete_item(item_id: int):
    """
    DELETE /item/{id} - мягкое удаление (deleted=True), идемпотентно
    """
    with _items_lock:
        existing = _items.get(item_id)
        if existing is not None:
            existing.deleted = True
    return {"ok": True}
