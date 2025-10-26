from collections import defaultdict
import secrets
from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter as PcCounter, Counter

app=FastAPI()
Instrumentator().instrument(app).expose(app,endpoint="/metrics",include_in_schema=False)
CART_CREATED=Counter("app_cart_created_total","total carts")
ITEM_ADDED=Counter("app_item_added_total","total items")
REQS_BY_PATH=PcCounter("app_requests_total","total q per path",["path"])

@app.middleware("http")
async def m(rq, nxt):
    if rq.url.path!="/metrics": REQS_BY_PATH.labels(path=rq.url.path).inc()
    return await nxt(rq)

class S:
    def __init__(s):
        s._i=0; s._c=0; s.items={}; s.carts={}
    def ni(s): s._i+=1; return s._i
    def nc(s): s._c+=1; return s._c
st=S()

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

def need_item(i):
    it=st.items.get(i) 
    if it is None: raise HTTPException(status_code=404,detail="Item not found")
    return it
def need_cart(c):
    ct=st.carts.get(c) # do we need it to check???
    if ct is None: raise HTTPException(status_code=404,detail="Cart not found")
    return ct

def cv(c):
    xs=[]; tot=0.0
    for iid,q in sorted(c["items"].items()):
        it=st.items.get(iid)
        if not it or it["deleted"]: continue
        xs.append({"id":iid,"quantity":int(q)})
        tot+=float(it["price"])*int(q)
    return {"id":c["id"],"items":xs,"price":float(tot)}

def sl(a,o,l): return a[o:o+l]

@app.post("/item",status_code=201)
def create_item(p=Body(...)):
    if not isinstance(p,dict): raise HTTPException(status_code=422,detail="Invalid body")
    if "name" not in p or "price" not in p: raise HTTPException(status_code=422,detail="name and price required")
    n=p["name"]; pr=gf(p["price"],"price")
    if pr is None or pr<0.0 or not isinstance(n,str) or not n: raise HTTPException(status_code=422,detail="Invalid fields")
    i=st.ni(); o={"id":i,"name":n,"price":float(pr),"deleted":False}; st.items[i]=o; return o

@app.get("/item/{item_id}")
def get_item(item_id):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    it=need_item(i)
    if it["deleted"]: raise HTTPException(status_code=404,detail="Item deleted")
    return it

@app.get("/item")
def list_items(offset=0,limit=10,min_price=None,max_price=None,show_deleted=False):
    o=gi(offset,"offset"); l=gi(limit,"limit"); mn=gf(min_price,"min_price"); mx=gf(max_price,"max_price"); sd=gb(show_deleted,False)
    if o is None or o<0: raise HTTPException(status_code=422,detail="offset")
    if l is None or l<=0: raise HTTPException(status_code=422,detail="limit")
    if mn is not None and mn<0: raise HTTPException(status_code=422,detail="min_price")
    if mx is not None and mx<0: raise HTTPException(status_code=422,detail="max_price")
    out=[]
    for iid in sorted(st.items.keys()):
        it=st.items[iid]
        if not sd and it["deleted"]: continue
        if mn is not None and it["price"]<float(mn): continue
        if mx is not None and it["price"]>float(mx): continue
        out.append(it)
    return sl(out,o,l)

@app.put("/item/{item_id}")
def put_item(item_id,p=Body(...)):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    it=need_item(i)
    if it["deleted"]: raise HTTPException(status_code=404,detail="Item deleted")
    if not isinstance(p,dict): raise HTTPException(status_code=422,detail="Invalid body")
    if "name" not in p or "price" not in p: raise HTTPException(status_code=422,detail="name and price required")
    n=p["name"]; pr=gf(p["price"],"price")
    if pr is None or pr<0.0 or not isinstance(n,str) or not n: raise HTTPException(status_code=422,detail="Invalid fields")
    it["name"]=n; it["price"]=float(pr); return it

@app.patch("/item/{item_id}")
def patch_item(item_id,body=Body(default={})):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    it=need_item(i)
    if it["deleted"]: return JSONResponse(status_code=304,content=None)
    if body is None: body={}
    if not isinstance(body,dict): raise HTTPException(status_code=422,detail="Invalid body")
    ok={"name","price"}
    if not set(body.keys()).issubset(ok): raise HTTPException(status_code=422,detail="Unexpected fields")
    if "name" in body:
        if not isinstance(body["name"],str) or not body["name"]: raise HTTPException(status_code=422,detail="Invalid name")
    if "price" in body:
        p=gf(body["price"],"price")
        if p is None or p<0.0: raise HTTPException(status_code=422,detail="Invalid price")
    if "name" in body: it["name"]=body["name"]
    if "price" in body: it["price"]=float(body["price"])
    return it

@app.delete("/item/{item_id}")
def delete_item(item_id):
    try: i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Item not found")
    it=st.items.get(i)
    if it is None: raise HTTPException(status_code=404,detail="Item not found")
    it["deleted"]=True
    return {"status":"ok"}

@app.post("/cart",status_code=201)
def create_cart():
    c=st.nc(); st.carts[c]={"id":c,"items":defaultdict(int)}; CART_CREATED.inc()
    return JSONResponse(status_code=201,content={"id":c},headers={"location":f"/cart/{c}"})

@app.get("/cart/{cart_id}")
def get_cart(cart_id):
    try: c=int(cart_id)
    except: raise HTTPException(status_code=404,detail="Cart not found")
    return cv(need_cart(c))

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id,item_id):
    try: c=int(cart_id); i=int(item_id)
    except: raise HTTPException(status_code=404,detail="Not found")
    cart=need_cart(c); it=need_item(i)
    if it["deleted"]: raise HTTPException(status_code=404,detail="Item deleted")
    cart["items"][i]=int(cart["items"].get(i,0))+1; ITEM_ADDED.inc()
    return cv(cart)

@app.get("/cart")
def list_carts(offset=0,limit=10,min_price=None,max_price=None,min_quantity=None,max_quantity=None):
    o=gi(offset,"offset"); l=gi(limit,"limit"); mn=gf(min_price,"min_price"); mx=gf(max_price,"max_price"); miq=gi(min_quantity,"min_quantity"); maq=gi(max_quantity,"max_quantity")
    if o is None or o<0: raise HTTPException(status_code=422,detail="offset")
    if l is None or l<=0: raise HTTPException(status_code=422,detail="limit")
    if mn is not None and mn<0: raise HTTPException(status_code=422,detail="min_price")
    if mx is not None and mx<0: raise HTTPException(status_code=422,detail="max_price")
    if miq is not None and miq<0: raise HTTPException(status_code=422,detail="min_quantity")
    if maq is not None and maq<0: raise HTTPException(status_code=422,detail="max_quantity")
    vs=[]
    for cid in sorted(st.carts.keys()):
        v=cv(st.carts[cid])
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
    for _ in range(5):
        n=f"user-{secrets.token_hex(3)}"
        if n not in _alloc:
            _alloc.add(n); return n
    return f"user-{secrets.token_hex(3)}"

async def _bcast(room,sender,text):
    nm=_usernames.get(sender,"user-unknown"); pl=f"{nm} :: {text}"
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