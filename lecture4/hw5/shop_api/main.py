from collections import defaultdict
import secrets
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Depends, HTTPException, Body, Response
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db, init_db
from .models import Item, Cart, CartItem
from sqlalchemy import select, func

try:
    from starlette.testclient import WebSocketTestSession as _WSTS
    _orig_close = _WSTS.close
    def _safe_close(self, code: int = 1000, reason: str | None = None):
        if not hasattr(self, "portal") or self.portal is None:
            return
        return _orig_close(self, code=code, reason=reason)
    _WSTS.close = _safe_close
except Exception:
    pass

app=FastAPI()
Instrumentator().instrument(app).expose(app)
REQS=Counter("app_requests_total","",["path"])
CARTS=Counter("app_cart_created_total","")
ADDED=Counter("app_item_added_total","")

@app.middleware("http")
async def _m(req, call_next):
    REQS.labels(path=req.url.path).inc()
    r=await call_next(req)
    return r

@app.on_event("startup")
def _st(): init_db()

@app.post("/item", status_code=201)
def create_item(name: str=Body(...), price: float=Body(...), db: Session=Depends(get_db)):
    it=Item(name=name, price=price, deleted=False)
    db.add(it); db.commit(); db.refresh(it)
    return {"id": it.id, "name": it.name, "price": float(it.price), "deleted": it.deleted}

@app.get("/item")
def list_items(offset: int=0, limit: int=100, min_price: float|None=None, max_price: float|None=None, show_deleted: bool=False, db: Session=Depends(get_db)):
    q=select(Item)
    if min_price is not None: q=q.where(Item.price>=min_price)
    if max_price is not None: q=q.where(Item.price<=max_price)
    if not show_deleted: q=q.where(Item.deleted==False)
    q=q.offset(offset).limit(limit)
    rows=db.execute(q).scalars().all()
    return [{"id":r.id,"name":r.name,"price":float(r.price),"deleted":r.deleted} for r in rows]

@app.get("/cart")
def list_carts(min_price: float|None=None, max_price: float|None=None, min_quantity: int|None=None, max_quantity: int|None=None, db: Session=Depends(get_db)):
    total_expr=func.coalesce(func.sum(Item.price*CartItem.quantity),0.0)
    qty_expr=func.coalesce(func.sum(CartItem.quantity),0)
    q=(db.query(Cart.id.label("id"), total_expr.label("total"), qty_expr.label("qty"))
        .select_from(Cart)
        .outerjoin(CartItem, CartItem.cart_id==Cart.id)
        .outerjoin(Item, Item.id==CartItem.item_id)
        .group_by(Cart.id))
    if min_price is not None: q=q.having(total_expr>=min_price)
    if max_price is not None: q=q.having(total_expr<=max_price)
    if min_quantity is not None: q=q.having(qty_expr>=min_quantity)
    if max_quantity is not None: q=q.having(qty_expr<=max_quantity)
    rows=q.all()
    return [{"id":r.id,"total_price":float(r.total),"total_quantity":int(r.qty)} for r in rows]

@app.get("/item/{item_id}")
def get_item(item_id: int, db: Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,"item not found")
    return {"id": it.id, "name": it.name, "price": float(it.price), "deleted": it.deleted}

@app.put("/item/{item_id}", status_code=204)
def put_item(item_id:int, name:str=Body(...), price:float=Body(...), db: Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,"item not found")
    it.name=name; it.price=price
    db.commit()
    return JSONResponse(status_code=204, content=None)

@app.patch("/item/{item_id}", status_code=204)
def patch_item(
    item_id: int,
    name: str | None = Body(None),
    price: float | None = Body(None),
    db: Session = Depends(get_db),
):
    it = db.get(Item, item_id)
    if not it:
        raise HTTPException(404, "item not found")
    if name is not None:
        it.name = name
    if price is not None:
        it.price = price
    db.commit()
    return Response(status_code=204)

@app.delete("/item/{item_id}", status_code=204)
def delete_item(item_id:int, db: Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,"item not found")
    it.deleted=True; db.commit()
    return JSONResponse(status_code=204, content=None)

@app.post("/cart", status_code=201)
def create_cart(db: Session=Depends(get_db)):
    c=Cart(); db.add(c); db.commit(); db.refresh(c); CARTS.inc()
    return {"id": c.id}

@app.post("/cart/{cart_id}/add/{item_id}", status_code=204)
def add_item_to_cart(cart_id:int, item_id:int, db: Session=Depends(get_db)):
    cart=db.get(Cart,cart_id)
    if not cart: raise HTTPException(404,"cart not found")
    it=db.get(Item,item_id)
    if not it or it.deleted: raise HTTPException(404,"item not found")
    ci=db.query(CartItem).filter_by(cart_id=cart_id,item_id=item_id).first()
    if ci: ci.quantity+=1
    else:
        ci=CartItem(cart_id=cart_id,item_id=item_id,quantity=1)
        db.add(ci)
    db.commit(); ADDED.inc()
    return JSONResponse(status_code=204, content=None)

@app.get("/cart/{cart_id}")
def get_cart(cart_id:int, db: Session=Depends(get_db)):
    cart=db.get(Cart,cart_id)
    if not cart: raise HTTPException(404,"cart not found")
    rows=(db.query(CartItem,Item).join(Item,Item.id==CartItem.item_id).filter(CartItem.cart_id==cart_id).all())
    items=[]; total=0.0
    for ci,it in rows:
        p=float(it.price); n=int(ci.quantity or 0); total+=p*n
        items.append({"item_id":it.id,"name":it.name,"price":p,"quantity":n})
    return {"id": cart.id, "items": items, "total_price": total}

_rooms=defaultdict(set)
_usernames={}
def _uname(): return "u"+secrets.token_hex(3)
async def _bcast(room,ws,txt):
    dead=[]
    for w in list(_rooms[room]):
        if w is ws: continue
        try: await w.send_text(txt)
        except: dead.append(w)
    for w in dead:
        _rooms[room].discard(w); _usernames.pop(w,None)

@app.websocket("/chat/{room}")
async def ws_chat(ws: WebSocket, room: str):
    await ws.accept(); u=_uname(); _rooms[room].add(ws); _usernames[ws]=u
    try:
        while True:
            m=await ws.receive_text()
            await _bcast(room,ws,m)
    except WebSocketDisconnect:
        pass
    finally:
        _rooms[room].discard(ws); _usernames.pop(ws,None)