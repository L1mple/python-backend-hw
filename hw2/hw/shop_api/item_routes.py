from fastapi import APIRouter, HTTPException, Depends
from http import HTTPStatus
from store.storage import local_storage
from contracts import ItemPatchRequest, ItemRequest, ItemModel, ListQueryModel
item_router = APIRouter(prefix="/item")

@item_router.post("/",
                  status_code=HTTPStatus.CREATED)
async def post_item(item_data: ItemRequest) -> ItemModel:
    item = local_storage.add_item(name=item_data.name, price=item_data.price)
    return ItemModel.from_entity(entity=item)

@item_router.get("/{item_id}",
                 status_code=HTTPStatus.OK)
async def get_item(item_id: int) -> ItemModel:
    try: 
       item = local_storage.get_item(id=item_id)
       return ItemModel.from_entity(item)
    except KeyError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="item not found")

@item_router.get("/")
async def get_item_list(query: ListQueryModel = Depends()) -> list[ItemModel]:
    items = local_storage.get_items(
        offset=query.offset,
        limit=query.limit,
        min_price=query.min_price,
        max_price=query.max_price,
        show_deleted=query.show_deleted
    )
    return [ItemModel.from_entity(item) for item in items]

@item_router.put("/{item_id}")
async def put_item(item_id: int, item_data:ItemRequest) -> ItemModel:
    item = local_storage.put_item(item_id = item_id,
                                  name = item_data.name,
                                  price = item_data.price)
    return ItemModel.from_entity(item)

@item_router.patch("/{item_id}")
async def patch_item(item_id: int, item_data: ItemPatchRequest) -> ItemModel:
    item = local_storage.patch_item(item_id=item_id,
                                    name = item_data.name,
                                    price = item_data.price)
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)
    return ItemModel.from_entity(item)              
    
@item_router.delete("/{item_id}")
async def patch_item(item_id: int) -> ItemModel:
    item = local_storage.soft_delete_item(item_id=item_id)
    return ItemModel.from_entity(item)              
    