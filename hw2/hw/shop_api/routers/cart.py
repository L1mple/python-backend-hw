from typing import List, Optional
from fastapi import APIRouter, Query, Response, status

from shop_api.core.schemas import CartView
from shop_api.core.storage import (
    _carts,
    _carts_lock,
    new_cart_id,
    cart_or_404,
    build_cart_view,
    get_item_or_404,
)

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    """
    POST /cart — RPC: создаёт пустую корзину, тело не принимает.
    Возвращает 201 и JSON {"id": <cart_id>}, а также заголовок Location: /cart/{id}.
    """
    cart_id = new_cart_id()
    with _carts_lock:
        _carts[cart_id] = {}
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@router.get("/{cart_id}", response_model=CartView)
def get_cart(cart_id: int) -> CartView:
    """
    GET /cart/{id} — получить корзину по id.
    """
    cart_or_404(cart_id)
    return build_cart_view(cart_id)


@router.get("", response_model=List[CartView])
def list_carts(
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
    with _carts_lock:
        ids = list(_carts.keys())

    views: List[CartView] = []
    for cid in ids:
        v = build_cart_view(cid)

        if min_price is not None and v.price < min_price:
            continue
        if max_price is not None and v.price > max_price:
            continue

        qsum = sum(it.quantity for it in v.items)
        if min_quantity is not None and qsum < min_quantity:
            continue
        if max_quantity is not None and qsum > max_quantity:
            continue

        views.append(v)

    return views[offset : offset + limit]


@router.post("/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    """
    POST /cart/{cart_id}/add/{item_id} — добавить товар в корзину.
    Если товар уже есть — увеличивает его количество.
    """
    cart = cart_or_404(cart_id)
    get_item_or_404(item_id)  # проверка на товар

    with _carts_lock:
        cart[item_id] = cart.get(item_id, 0) + 1

    return {"ok": True}
