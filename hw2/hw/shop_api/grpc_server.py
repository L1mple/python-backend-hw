import asyncio
from concurrent import futures

import grpc

from . import schemas
from .storage import (
    add_to_cart as db_add_to_cart,
    cart_to_model as db_cart_to_model,
    create_cart as db_create_cart,
    create_item as db_create_item,
    get_item as db_get_item,
)
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


def to_pb_cart(cart_id: int) -> PbCart:
    model = db_cart_to_model(cart_id)
    if model is None:
        # Should be validated by caller
        return PbCart(id=cart_id, items=[], price=0.0)
    items = [PbCartItem(id=ci.id, quantity=ci.quantity) for ci in model.items]
    return PbCart(id=model.id, items=items, price=model.price)


class ShopService(ShopServicer):
    def CreateCart(self, request: PbEmpty, context: grpc.ServicerContext) -> PbId:  
        cid = db_create_cart()
        return PbId(id=cid)

    def GetCart(self, request: PbId, context: grpc.ServicerContext) -> PbCart:  
        cid = request.id
        if db_cart_to_model(cid) is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Cart not found")
        return to_pb_cart(cid)

    def AddToCart(self, request: PbAddToCartRequest, context: grpc.ServicerContext) -> PbCart:  
        cid = request.cart_id
        iid = request.item_id
        try:
            model = db_add_to_cart(cid, iid)
        except KeyError:
            context.abort(grpc.StatusCode.NOT_FOUND, "Item not found")
        if model is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Cart not found")
        return to_pb_cart(cid)

    def CreateItem(self, request: PbItemCreate, context: grpc.ServicerContext) -> PbItem:  
        item = db_create_item(request.name, request.price)
        return PbItem(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

    def GetItem(self, request: PbId, context: grpc.ServicerContext) -> PbItem:  
        item = db_get_item(request.id)
        if item is None:
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


