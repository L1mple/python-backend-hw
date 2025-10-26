from fastapi import APIRouter, HTTPException, Depends
from http import HTTPStatus
from sqlalchemy.orm import Session
from shop_api.store.db_storage import DBStorage
from shop_api.database import get_db
from shop_api.contracts import ItemPatchRequest, ItemRequest, ItemModel, ListQueryModel
item_router = APIRouter(prefix="/item")

@item_router.post("/",
                  status_code=HTTPStatus.CREATED)
async def post_item(item_data: ItemRequest, db: Session = Depends(get_db)) -> ItemModel:
    storage = DBStorage(db=db)
    item = storage.add_item(name=item_data.name, price=item_data.price)
    return ItemModel.from_entity(entity=item)

@item_router.get("/{item_id}",
                 status_code=HTTPStatus.OK)
async def get_item(item_id: int, db: Session = Depends(get_db)) -> ItemModel:
    storage = DBStorage(db=db)
    try:
       item = storage.get_item(id=item_id)
       return ItemModel.from_entity(item)
    except KeyError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="item not found")

@item_router.get("/")
async def get_item_list(query: ListQueryModel = Depends(), db: Session = Depends(get_db)) -> list[ItemModel]:
    storage = DBStorage(db=db)
    items = storage.get_items(
        offset=query.offset,
        limit=query.limit,
        min_price=query.min_price,
        max_price=query.max_price,
        show_deleted=query.show_deleted
    )
    return [ItemModel.from_entity(item) for item in items]

@item_router.put("/{item_id}")
async def put_item(item_id: int, item_data:ItemRequest, db: Session = Depends(get_db)) -> ItemModel:
    storage = DBStorage(db=db)
    item = storage.put_item(item_id = item_id,
                                  name = item_data.name,
                                  price = item_data.price)
    return ItemModel.from_entity(item)

@item_router.patch("/{item_id}")
async def patch_item(item_id: int, item_data: ItemPatchRequest, db: Session = Depends(get_db)) -> ItemModel:
    storage = DBStorage(db=db)
    item = storage.patch_item(item_id=item_id,
                                    name = item_data.name,
                                    price = item_data.price)
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)
    return ItemModel.from_entity(item)

@item_router.delete("/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)) -> ItemModel:
    storage = DBStorage(db=db)
    item = storage.soft_delete_item(item_id=item_id)
    return ItemModel.from_entity(item)              
    