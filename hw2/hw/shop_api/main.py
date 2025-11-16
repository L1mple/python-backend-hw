from fastapi import FastAPI, HTTPException, Query, Body, WebSocket

from typing import Dict, Any, List, Optional
from fastapi.responses import JSONResponse
from fastapi import WebSocketDisconnect

from uuid import uuid4

app = FastAPI(title="Shop API")

class S:
    def __init__(self):
        self.items: Dict[int, Dict[str, Any]] = {}
        self.carts: Dict[int, Dict[int, int]] = {}
        self.iid = 1
        self.cid = 1

    def mk_item(self, name: str, price: float) -> Dict[str, Any]:
        i = self.iid
        self.iid += 1
        self.items[i] = {"id": i, "name": name, "price": float(price), "deleted": False}
        return self.items[i]

    def one_item(self, i: int) -> Dict[str, Any]:
        x = self.items.get(i)
        if not x or x["deleted"]:
            raise HTTPException(status_code=404)
        return x

    def set_item(self, i: int, name: str, price: float) -> Dict[str, Any]:
        if i not in self.items or self.items[i]["deleted"]:
            raise HTTPException(status_code=404)
        self.items[i]["name"] = name
        self.items[i]["price"] = float(price)
        return self.items[i]

    def patch_item(self, i: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if i not in self.items:
            raise HTTPException(status_code=404)
        if self.items[i]["deleted"]:
            return None
        if set(data.keys()) - {"name", "price"}:
            raise HTTPException(status_code=422)
        if "name" in data:
            self.items[i]["name"] = data["name"]
        if "price" in data:
            self.items[i]["price"] = float(data["price"])
        return self.items[i]

    def del_item(self, i: int) -> None:
        if i in self.items:
            self.items[i]["deleted"] = True

    def mk_cart(self) -> int:
        c = self.cid
        self.cid += 1
        self.carts[c] = {}
        return c

    def cart_view(self, c: int) -> Dict[str, Any]:
        if c not in self.carts:
            raise HTTPException(status_code=404)
        arr = []
        total = 0.0
        for iid, q in self.carts[c].items():
            it = self.items.get(iid)
            ok = bool(it and not it["deleted"])
            nm = it["name"] if it else "unknown"
            arr.append({"id": iid, "name": nm, "quantity": q, "available": ok})
            if ok:
                total += float(it["price"]) * q
        return {"id": c, "items": arr, "price": float(total)}

    def add(self, c: int, i: int) -> None:
        if c not in self.carts:
            raise HTTPException(status_code=404)
        if i not in self.items:
            raise HTTPException(status_code=404)
        d = self.carts[c]
        d[i] = d.get(i, 0) + 1

st = S()

def _slice(x: List[Any], o: int, l: int) -> List[Any]:
    return x[o:o+l]

@app.post("/item", status_code=201)
def create_item(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    if "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    return st.mk_item(body["name"], body["price"])

@app.get("/item/{item_id}")
def read_item(item_id: int) -> Dict[str, Any]:
    return st.one_item(item_id)

@app.get("/item")
def read_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
) -> List[Dict[str, Any]]:
    xs = list(st.items.values())
    if not show_deleted:
        xs = [x for x in xs if not x["deleted"]]
    if min_price is not None:
        xs = [x for x in xs if float(x["price"]) >= float(min_price)]
    if max_price is not None:
        xs = [x for x in xs if float(x["price"]) <= float(max_price)]
    xs.sort(key=lambda x: x["id"])
    return _slice(xs, offset, limit)

@app.put("/item/{item_id}")
def replace_item(item_id: int, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    if set(body.keys()) - {"name", "price"}:
        raise HTTPException(status_code=422)
    if "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    return st.set_item(item_id, body["name"], body["price"])

@app.patch("/item/{item_id}")
def update_item(item_id: int, body: Dict[str, Any] = Body(...)):
    y = st.patch_item(item_id, body)
    if y is None:
        return JSONResponse(status_code=304, content=None)
    return y

@app.delete("/item/{item_id}")
def remove_item(item_id: int):
    st.del_item(item_id)
    return {"ok": True}

@app.post("/cart", status_code=201)
def create_cart():
    cid = st.mk_cart()
    return JSONResponse(status_code=201, content={"id": cid}, headers={"location": f"/cart/{cid}"})

@app.get("/cart/{cart_id}")
def read_cart(cart_id: int):
    return st.cart_view(cart_id)

@app.get("/cart")
def read_carts(
    skip: int = Query(0, ge=0, alias="offset"),
    take: int = Query(10, gt=0, alias="limit"),
    pmin: Optional[float] = Query(None, ge=0, alias="min_price"),
    pmax: Optional[float] = Query(None, ge=0, alias="max_price"),
    qmin: Optional[int] = Query(None, ge=0, alias="min_quantity"),
    qmax: Optional[int] = Query(None, ge=0, alias="max_quantity"),
) -> List[Dict[str, Any]]:
    bag = []
    for k in sorted(st.carts):
        v = st.cart_view(k)
        tot = 0
        for it in v["items"]:
            tot += it["quantity"]
        if pmin is not None and v["price"] < float(pmin):
            continue
        if pmax is not None and v["price"] > float(pmax):
            continue
        if qmin is not None and tot < int(qmin):
            continue
        if qmax is not None and tot > int(qmax):
            continue
        bag.append(v)
    if skip >= len(bag):
        return []
    return bag[skip:skip + take]

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item(cart_id: int, item_id: int):
    st.add(cart_id, item_id)
    return {"ok": True}

_rooms: Dict[str, List[WebSocket]] = {}
_names: Dict[WebSocket, str] = {}

@app.websocket("/chat/{room}")
async def ws_chat(ws: WebSocket, room: str):
    await ws.accept()
    u = "user-" + uuid4().hex[:6]
    _names[ws] = u
    _rooms.setdefault(room, []).append(ws)
    try:
        while True:
            t = await ws.receive_text()
            for w in list(_rooms.get(room, [])):
                if w is not ws:
                    try:
                        await w.send_text(f"{u} :: {t}")
                    except RuntimeError:
                        pass
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _rooms.get(room, []):
            _rooms[room].remove(ws)
        _names.pop(ws, None)
        if _rooms.get(room) == []:
            _rooms.pop(room, None)