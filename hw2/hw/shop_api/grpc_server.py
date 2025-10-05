import asyncio
from concurrent import futures

import grpc

from . import schemas
from .storage import carts_items, items_by_id, next_cart_id, next_item_id
from .shop_pb2 import (
    AddToCartRequest as PbAddToCartRequest,
    Cart as PbCart,
    CartItem as PbCartItem,
    Empty as PbEmpty,
    Id as PbId,
    Item as PbItem,
    ItemCreate as PbItemCreate,
)
from .shop_pb2_grpc import ShopServicer, add_ShopServicer_to_server


def compute_cart_price(cart_map: dict[int, int]) -> float:
    total = 0.0
    for item_id, quantity in cart_map.items():
        item = items_by_id.get(item_id)
        if item is None or item.deleted:
            continue
        total += item.price * quantity
    return total


def to_pb_cart(cart_id: int) -> PbCart:
    cart_map = carts_items.get(cart_id, {})
    items = [PbCartItem(id=iid, quantity=qty) for iid, qty in cart_map.items()]
    return PbCart(id=cart_id, items=items, price=compute_cart_price(cart_map))


class ShopService(ShopServicer):
    def CreateCart(self, request: PbEmpty, context: grpc.ServicerContext) -> PbId:  
        global next_cart_id
        cid = next_cart_id
        carts_items[cid] = {}
        next_cart_id += 1
        return PbId(id=cid)

    def GetCart(self, request: PbId, context: grpc.ServicerContext) -> PbCart:  
        cid = request.id
        if cid not in carts_items:
            context.abort(grpc.StatusCode.NOT_FOUND, "Cart not found")
        return to_pb_cart(cid)

    def AddToCart(self, request: PbAddToCartRequest, context: grpc.ServicerContext) -> PbCart:  
        cid = request.cart_id
        iid = request.item_id
        cart = carts_items.get(cid)
        if cart is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Cart not found")
        item = items_by_id.get(iid)
        if item is None or item.deleted:
            context.abort(grpc.StatusCode.NOT_FOUND, "Item not found")
        cart[iid] = cart.get(iid, 0) + 1
        return to_pb_cart(cid)

    def CreateItem(self, request: PbItemCreate, context: grpc.ServicerContext) -> PbItem:  
        global next_item_id
        iid = next_item_id
        item = schemas.Item(id=iid, name=request.name, price=request.price, deleted=False)
        items_by_id[iid] = item
        next_item_id += 1
        return PbItem(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

    def GetItem(self, request: PbId, context: grpc.ServicerContext) -> PbItem:  
        item = items_by_id.get(request.id)
        if item is None or item.deleted:
            context.abort(grpc.StatusCode.NOT_FOUND, "Item not found")
        return PbItem(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


def serve(block: bool = True) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ShopServicer_to_server(ShopService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    if block:
        server.wait_for_termination()
    return server


if __name__ == "__main__":
    serve(block=True)


