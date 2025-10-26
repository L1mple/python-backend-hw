
from typing import List, Optional
from fastapi import APIRouter, Query, Response, status

from shop_api.core.schemas import CartView
from shop_api.core import storage

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response):
    """
    POST /cart — RPC: создаёт пустую корзину, тело не принимает.
    Возвращает 201 и JSON {"id": <cart_id>}, а также заголовок Location: /cart/{id}.
    """
    cart_id = await storage.create_cart()
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@router.get("/{cart_id}", response_model=CartView)
async def get_cart(cart_id: int) -> CartView:
    """
    GET /cart/{id} — получить корзину по id.
    """
    return await storage.build_cart_view(cart_id)


@router.get("", response_model=List[CartView])
async def list_carts(
    offset: int = Query(0, ge=0, description="Смещение по списку (offset)"),
    limit: int = Query(10, gt=0, description="Лимит количества (limit)"),
    min_price: Optional[float] = Query(
        None, ge=0.0, description="Мин. сумма корзины (включительно)"
    ),
    max_price: Optional[float] = Query(
        None, ge=0.0, description="Макс. сумма корзины (включительно)"
    ),
    min_quantity: Optional[int] = Query(
        None, ge=0, description="Мин. общее число товаров (включительно)"
    ),
    max_quantity: Optional[int] = Query(
        None, ge=0, description="Макс. общее число товаров (включительно)"
    ),
) -> List[CartView]:
    """
    GET /cart — список корзин с фильтрами и пагинацией.

    Фильтры:
      • min_price/max_price — по суммарной стоимости корзины (включительно);
      • min_quantity/max_quantity — по суммарному количеству позиций в корзине (включительно).
    Порядок: фильтрация -> offset/limit.
    """
    return await storage.list_carts(offset=offset, limit=limit, min_price=min_price, max_price=max_price, min_quantity=min_quantity, max_quantity=max_quantity)


@router.post("/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    """
    POST /cart/{cart_id}/add/{item_id} — добавить товар в корзину.
    Если товар уже есть — увеличивает его количество.
    """
    return await storage.add_to_cart(cart_id, item_id)
