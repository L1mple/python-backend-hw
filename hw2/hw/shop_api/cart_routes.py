from fastapi import APIRouter, Response, HTTPException, Depends
from http import HTTPStatus
from store.storage import local_storage
from contracts import IdModel, CartResponseModel, ListQueryModel
cart_router = APIRouter(prefix="/cart")

@cart_router.post("/",
                  status_code=HTTPStatus.CREATED)
async def post_cart(response: Response): 
    cart = local_storage.create_cart()
    response.headers["location"] = f"/cart/{cart.id}"
    return IdModel(id=cart.id)


@cart_router.post("/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int):
    success = local_storage.add_item_to_cart(cart_id, item_id)
    if not success:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return {"message": "Item added to cart"}

@cart_router.get("/{cart_id}",
                 status_code=HTTPStatus.OK)
async def get_cart(cart_id: int) -> CartResponseModel:
    try: 
       cart = local_storage.get_cart(id=cart_id)
       return CartResponseModel.from_entity(cart)
    except KeyError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="cart not found")


@cart_router.get("/")
async def get_item_list(query: ListQueryModel = Depends()) -> list[CartResponseModel]:
    carts = local_storage.get_carts(
        offset=query.offset,
        limit=query.limit,
        min_price=query.min_price,
        max_price=query.max_price,
        min_quantity=query.min_quantity,
        max_quantity=query.max_quantity
    )
    return [CartResponseModel.from_entity(cart) for cart in carts]