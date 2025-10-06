from dataclasses import asdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from shop_api.models.item import ItemCreate, ItemOut, ItemPatch, ItemPut, ItemRecord
from shop_api.storage.in_mem import get_store

router = APIRouter(prefix="/item", tags=["item"])


@router.get("", response_model=list[ItemOut], status_code=HTTPStatus.OK)
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    show_deleted: bool = Query(False),
    deps=Depends(get_store),
):
    items: ItemRecord
    items, _, _ = deps
    result: list[ItemOut] = []
    for iid, data in items.items():
        if not show_deleted and data.deleted:
            continue
        if min_price is not None and data.price < min_price:
            continue
        if max_price is not None and data.price > max_price:
            continue
        result.append(ItemOut(id=iid, **asdict(data)))
    return result[offset : offset + limit]


@router.get("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def item_by_id(
    item_id: int,
    deps=Depends(get_store),
):
    items, _, _ = deps
    rec: None | ItemRecord = items.get(item_id)
    if rec is None or rec.deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail={"error": "item not found"}
        )
    return ItemOut(id=item_id, **asdict(items[item_id]))


@router.post("", response_model=ItemOut, status_code=HTTPStatus.CREATED)
async def create_item(
    payload: ItemCreate,
    request: Request,
    deps=Depends(get_store),
):
    items, _, lock = deps
    async with lock:
        new_id = request.app.state.last_item_id + 1
        request.app.state.last_item_id = new_id
        items[new_id] = ItemRecord(
            name=payload.name,
            price=payload.price,
            description=payload.description,
            deleted=False,
        )
    return ItemOut(id=new_id, **asdict(items[new_id]))


@router.put("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def put_item(
    item_id: int,
    payload: ItemPut,
    deps=Depends(get_store),
):
    items, _, lock = deps
    async with lock:
        if item_id not in items:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail={
                    "error": "item not found",
                },
            )
        items[item_id] = ItemRecord(
            name=payload.name,
            price=payload.price,
            description=payload.description,
            deleted=False,
        )
    return ItemOut(id=item_id, **asdict(items[item_id]))


@router.patch("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def patch_item(
    item_id: int,
    payload: ItemPatch,
    deps=Depends(get_store),
):
    items, _, locks = deps
    async with locks:
        item = items.get(item_id)
        if item is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail={
                    "error": "item not found",
                },
            )

        if item.deleted:
            raise HTTPException(
                status_code=HTTPStatus.NOT_MODIFIED,
                detail={"error": "item is deleted"},
            )

        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        for k, v in update_data.items():
            setattr(item, k, v)
    return ItemOut(id=item_id, **asdict(item))


@router.delete("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def delete_item(
    item_id: int,
    deps=Depends(get_store),
):
    items, _, locks = deps
    async with locks:
        rec = items.get(item_id)
        if rec is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail={"error": "item not found"}
            )
        rec.deleted = True
        return ItemOut(id=item_id, **asdict(items[item_id]))
