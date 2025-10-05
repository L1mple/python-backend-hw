from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Id(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class ItemCreate(_message.Message):
    __slots__ = ("name", "price")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    name: str
    price: float
    def __init__(self, name: _Optional[str] = ..., price: _Optional[float] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("id", "name", "price", "deleted")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    price: float
    deleted: bool
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., price: _Optional[float] = ..., deleted: bool = ...) -> None: ...

class CartItem(_message.Message):
    __slots__ = ("id", "quantity")
    ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    id: int
    quantity: int
    def __init__(self, id: _Optional[int] = ..., quantity: _Optional[int] = ...) -> None: ...

class Cart(_message.Message):
    __slots__ = ("id", "items", "price")
    ID_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    id: int
    items: _containers.RepeatedCompositeFieldContainer[CartItem]
    price: float
    def __init__(self, id: _Optional[int] = ..., items: _Optional[_Iterable[_Union[CartItem, _Mapping]]] = ..., price: _Optional[float] = ...) -> None: ...

class AddToCartRequest(_message.Message):
    __slots__ = ("cart_id", "item_id")
    CART_ID_FIELD_NUMBER: _ClassVar[int]
    ITEM_ID_FIELD_NUMBER: _ClassVar[int]
    cart_id: int
    item_id: int
    def __init__(self, cart_id: _Optional[int] = ..., item_id: _Optional[int] = ...) -> None: ...
