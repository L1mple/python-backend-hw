from collections import defaultdict
import secrets


from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse



from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter as PcCounter, Counter

from sqlalchemy import select, update, func



from .db import SessionLocal, init_db
from .models import Item, Cart, CartItem

app=FastAPI()
Instrumentator().instrument(app).expose(app,endpoint="/metrics",include_in_schema=False)
CART_CREATED=Counter("app_cart_created_total","total carts")
ITEM_ADDED=Counter("app_item_added_total","total items")
REQS_BY_PATH=PcCounter("app_requests_total","total q per path",["path"])

@app.on_event("startup")
def _s(): init_db()

@app.middleware("http")
async def m(rq, nxt):
    if rq.url.path!="/metrics": REQS_BY_PATH.labels(path=rq.url.path).inc()
    return await nxt(rq)

def gi(x,n):
    if x is None: return None
    try: return int(x)
    except: raise HTTPException(status_code=422,detail=f"Invalid {n}")
def gf(x,n):
    if x is None: return None
    try: return float(x)
    except: raise HTTPException(status_code=422,detail=f"Invalid {n}")
def gb(x,d=False):
    if isinstance(x,bool): return x
    if x is None: return d
    s=str(x).lower()
    if s in ("1","true","yes","on"): return True
    if s in ("0","false","no","off"): return False
    return d

def sl(a,o,l): return a[o:o+l]

def need_item(db,i):
    it=db.get(Item,i)
    if not it or it.deleted: raise HTTPException(status_code=404,detail="Item not found")
    return it
def need_cart(db,c):
    ct=db.get(Cart,c)
    if not ct: raise HTTPException(status_code=404,detail="Cart not found")
    return ct

def cv(db,c):
    rows=db.execute(select(CartItem,Item).join(Item,CartItem.item_id==Item.id).where(CartItem.cart_id==c.id,Item.deleted==False).order_by(Item.id)).all()
    xs=[]; tot=0.0
    for ci,it in rows:
        xs.append({"id":it.id,"quantity":int(ci.quantity)})
        tot+=float(it.price)*int(ci.quantity)
    return {"id":c.id,"items":xs,"price":float(tot)}

@app.post("/item",status_code=201)
def create_item(p=Body(...)):
    if not isinstance(p,dict): raise HTTPException(status_code=422,detail="Invalid body")
    if "name" not in p or "price" not in p: raise HTTPException(status_code=422,detail="name and price required")
    n=p["name"]; pr=gf(p["price"],"price")
    if pr is None or pr<0.0 or not isinstance(n,str) or not n: raise HTTPException(status_code=422,detail="Invalid fields")
    with SessionLocal.begin() as db:
        it=Item(name=n,price=float(pr),deleted=False); db.add(it); db.flush()
        return {"id":it.id,"name":it.name,"price":float(it.price),"deleted":it.deleted}

@app.get("/item/{item_id}")
def get_item(item_id):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    with SessionLocal() as db:
        it=need_item(db,i)
        return {"id":it.id,"name":it.name,"price":float(it.price),"deleted":it.deleted}

@app.get("/item")
def list_items(offset=0,limit=10,min_price=None,max_price=None,show_deleted=False):
    o=gi(offset,"offset"); l=gi(limit,"limit"); mn=gf(min_price,"min_price"); mx=gf(max_price,"max_price"); sd=gb(show_deleted,False)
    if o is None or o<0: raise HTTPException(status_code=422,detail="offset")
    if l is None or l<=0: raise HTTPException(status_code=422,detail="limit")
    if mn is not None and mn<0: raise HTTPException(status_code=422,detail="min_price")
    if mx is not None and mx<0: raise HTTPException(status_code=422,detail="max_price")
    with SessionLocal() as db:
        q=select(Item).order_by(Item.id)
        if not sd: q=q.where(Item.deleted==False)
        if mn is not None: q=q.where(Item.price>=float(mn))
        if mx is not None: q=q.where(Item.price<=float(mx))
        rows=db.execute(q).scalars().all()
        out=[{"id":it.id,"name":it.name,"price":float(it.price),"deleted":it.deleted} for it in rows]
        return sl(out,o,l)

@app.put("/item/{item_id}")
def put_item(item_id,p=Body(...)):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    if not isinstance(p,dict): raise HTTPException(status_code=422,detail="Invalid body")
    if "name" not in p or "price" not in p: raise HTTPException(status_code=422,detail="name and price required")
    n=p["name"]; pr=gf(p["price"],"price")
    if pr is None or pr<0.0 or not isinstance(n,str) or not n: raise HTTPException(status_code=422,detail="Invalid fields")
    with SessionLocal.begin() as db:
        it=need_item(db,i); it.name=n; it.price=float(pr); db.flush()
        return {"id":it.id,"name":it.name,"price":float(it.price),"deleted":it.deleted}

@app.patch("/item/{item_id}")
def patch_item(item_id,body=Body(default={})):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    if body is None: body={}
    if not isinstance(body,dict): raise HTTPException(status_code=422,detail="Invalid body")
    ok={"name","price"}
    if not set(body.keys()).issubset(ok): raise HTTPException(status_code=422,detail="Unexpected fields")
    with SessionLocal.begin() as db:
        it=need_item(db,i)
        if it.deleted: return JSONResponse(status_code=304,content=None)
        if "name" in body:
            if not isinstance(body["name"],str) or not body["name"]: raise HTTPException(status_code=422,detail="Invalid name")
            it.name=body["name"]
        if "price" in body:
            p=gf(body["price"],"price")
            if p is None or p<0.0: raise HTTPException(status_code=422,detail="Invalid price")
            it.price=float(body["price"])
        db.flush()
        return {"id":it.id,"name":it.name,"price":float(it.price),"deleted":it.deleted}

@app.delete("/item/{item_id}")
def delete_item(item_id):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    with SessionLocal.begin() as db:
        it=db.get(Item,i)
        if not it: raise HTTPException(status_code=404,detail="Item not found")
        it.deleted=True; db.flush()
        return {"status":"ok"}

@app.post("/cart",status_code=201)
def create_cart():
    with SessionLocal.begin() as db:
        ct=Cart(); db.add(ct); db.flush(); CART_CREATED.inc()
        return JSONResponse(status_code=201,content={"id":ct.id},headers={"location":f"/cart/{ct.id}"})

@app.get("/cart/{cart_id}")
def get_cart(cart_id):
    try: c=int(cart_id)
    except: raise HTTPException(status_code=404,detail="Cart not found")
    with SessionLocal() as db:
        return cv(db,need_cart(db,c))

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id,item_id):
    try: c=int(cart_id); i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Not found")
    with SessionLocal.begin() as db:
        cart=need_cart(db,c); it=need_item(db,i)
        ci=db.get(CartItem,{"cart_id":cart.id,"item_id":it.id})
        if ci: ci.quantity=int(ci.quantity)+1
        else: ci=CartItem(cart_id=cart.id,item_id=it.id,quantity=1); db.add(ci)
        ITEM_ADDED.inc(); db.flush()
        return cv(db,cart)

@app.get("/cart")
def list_carts(offset=0,limit=10,min_price=None,max_price=None,min_quantity=None,max_quantity=None):
    o=gi(offset,"offset"); l=gi(limit,"limit"); mn=gf(min_price,"min_price"); mx=gf(max_price,"max_price"); miq=gi(min_quantity,"min_quantity"); maq=gi(max_quantity,"max_quantity")
    if o is None or o<0: raise HTTPException(status_code=422,detail="offset")
    if l is None or l<=0: raise HTTPException(status_code=422,detail="limit")
    if mn is not None and mn<0: raise HTTPException(status_code=422,detail="min_price")
    if mx is not None and mx<0: raise HTTPException(status_code=422,detail="max_price")
    if miq is not None and miq<0: raise HTTPException(status_code=422,detail="min_quantity")
    if maq is not None and maq<0: raise HTTPException(status_code=422,detail="max_quantity")
    with SessionLocal() as db:
        ids=[x.id for x in db.execute(select(Cart).order_by(Cart.id)).scalars().all()]
        vs=[]
        for cid in ids:
            v=cv(db,db.get(Cart,cid))
            if mn is not None and v["price"]<float(mn): continue
            if mx is not None and v["price"]>float(mx): continue
            q=sum(i["quantity"] for i in v["items"])
            if miq is not None and q<int(miq): continue
            if maq is not None and q>int(maq): continue
            vs.append(v)
        return sl(vs,o,l)

_rooms=defaultdict(set)
_usernames={}
_alloc=set()

def _uname():
    while True:
        u="u"+secrets.token_hex(2)
        if u not in _alloc: _alloc.add(u); return u

async def _bcast(room,sender,msg):
    u=_usernames.get(sender,"anon")
    pl=f"{u}: {msg}"
    dead=[]
    for ws in list(_rooms[room]):
        if ws is sender: continue
        try: await ws.send_text(pl)
        except: dead.append(ws)
    for ws in dead:
        _rooms[room].discard(ws); _usernames.pop(ws,None)

@app.websocket("/chat/{room}")
async def ws_chat(ws,room):
    await ws.accept(); u=_uname(); _rooms[room].add(ws); _usernames[ws]=u
    try:
        while True:
            m=await ws.receive_text()
            await _bcast(room,ws,m)
    except WebSocketDisconnect:
        pass
    finally:
        _rooms[room].discard(ws); _usernames.pop(ws,None)