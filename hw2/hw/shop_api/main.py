from fastapi import FastAPI, HTTPException, Query, Path, Response
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="Shop API")

ITEMS = {}  # товары{"id","name","price","deleted"}
CARTS = {}  # корзина{item_id: quantity}
_item_id = 1
_cart_id = 1

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)

class ItemPut(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)

class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0.0)
    class Config:
        extra = "forbid"

class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

# utils
def get_item_or_404(item_id: int, allow_deleted: bool = False):
    """Возвращает товар по id (или 404, если не найден)"""
    it = ITEMS.get(item_id)
    if not it:
        raise HTTPException(404, "Item not found")
    if it["deleted"] and not allow_deleted:
        raise HTTPException(404, "Item not found")
    return it

def get_cart_or_404(cart_id: int):
    """Возвращает корзину по id (или 404, если не найдена)"""
    cart = CARTS.get(cart_id)
    if cart is None:
        raise HTTPException(404, "Cart not found")
    return cart

def cart_snapshot(cart_id: int):
    """Формирует текущее состояние корзины с товарами и общей ценой"""
    cart = get_cart_or_404(cart_id)
    items_out = []
    total = 0.0
    for iid, qty in cart.items():
        it = ITEMS.get(iid)
        if not it:
            continue
        items_out.append(CartItemOut(
            id=it["id"],
            name=it["name"],
            quantity=qty,
            available=not it["deleted"],
        ))
        total += float(it["price"]) * qty  # по текущей цене
    return CartOut(id=cart_id, items=items_out, price=total)

# cart
@app.post("/cart", status_code=201)
def create_cart(response: Response):
    """Создаёт новую корзину и возвращает её id"""
    global _cart_id
    cid = _cart_id
    _cart_id += 1
    CARTS[cid] = {}
    response.headers["Location"] = f"/cart/{cid}"
    return {"id": cid}

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int = Path(..., ge=1)):
    """Возвращает корзину по id"""
    return cart_snapshot(cart_id)

@app.get("/cart", response_model=List[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    """Возвращает список корзин с фильтрами и пагинацией"""
    snaps = []
    for cid in sorted(CARTS.keys()):
        snap = cart_snapshot(cid)
        qty = sum(ci.quantity for ci in snap.items)
        if min_quantity is not None and qty < min_quantity:
            continue
        if max_quantity is not None and qty > max_quantity:
            continue
        if min_price is not None and snap.price < min_price:
            continue
        if max_price is not None and snap.price > max_price:
            continue
        snaps.append(snap)
    return snaps[offset: offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int = Path(..., ge=1), item_id: int = Path(..., ge=1)):
    """Добавляет товар в корзину/увеличивает кол-во, если уже есть"""
    cart = get_cart_or_404(cart_id)
    it = get_item_or_404(item_id, allow_deleted=True)
    if it["deleted"]:
        raise HTTPException(400, "Cannot add a deleted item to cart")
    cart[item_id] = cart.get(item_id, 0) + 1
    return cart_snapshot(cart_id)

# --- item ---
@app.post("/item", response_model=ItemOut, status_code=201)
def create_item(body: ItemCreate):
    """Создаёт новый товар"""
    global _item_id
    iid = _item_id
    _item_id += 1
    ITEMS[iid] = {"id": iid, "name": body.name, "price": float(body.price), "deleted": False}
    return ItemOut(**ITEMS[iid])

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int = Path(..., ge=1)):
    """Возвращает товар по id (404, если удалён)"""
    return ItemOut(**get_item_or_404(item_id))

@app.get("/item", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    """Возвращает список товаров с фильтрацией и пагинацией"""
    out = []
    for iid in sorted(ITEMS.keys()):
        it = ITEMS[iid]
        if not show_deleted and it["deleted"]:
            continue
        if min_price is not None and float(it["price"]) < min_price:
            continue
        if max_price is not None and float(it["price"]) > max_price:
            continue
        out.append(ItemOut(**it))
    return out[offset: offset + limit]

@app.put("/item/{item_id}", response_model=ItemOut)
def put_item(item_id: int = Path(..., ge=1), body: ItemPut = ...):
    """Полностью обновляет товар (name/price)"""
    it = get_item_or_404(item_id)
    it["name"] = body.name
    it["price"] = float(body.price)
    return ItemOut(**it)

@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int = Path(..., ge=1), body: ItemPatch = ...):
    """Частично обновляет товар. Если удалён — 304"""
    it = get_item_or_404(item_id, allow_deleted=True)
    if it["deleted"]:
        return Response(status_code=304)
    if body.name is not None:
        it["name"] = body.name
    if body.price is not None:
        it["price"] = float(body.price)
    return ItemOut(**it)

@app.delete("/item/{item_id}")
def delete_item(item_id: int = Path(..., ge=1)):
    """Помечает товар как удалённый (200 OK)"""
    it = get_item_or_404(item_id, allow_deleted=True)
    it["deleted"] = True
    return {} 