from __future__ import annotations

from typing import List

from fastapi import HTTPException, status

from .exceptions import ItemDeletedError, ItemNotFoundError
from .models import (
    CartCreateResponse,
    CartItemResponse,
    CartListQuery,
    CartResponse,
    ItemCreateRequest,
    ItemCreateResponse,
    ItemListQuery,
    ItemPatchRequest,
    ItemResponse,
    ItemUpdateRequest,
)
from .repositories import CartRepository, ItemRepository


class ItemService:
    def __init__(self, repo: ItemRepository):
        self._repo = repo

    def create(self, request: ItemCreateRequest) -> ItemCreateResponse:
        item = self._repo.create(name=request.name, price=request.price)
        return ItemCreateResponse(**item.__dict__)

    def get(self, item_id: int) -> ItemResponse:
        try:
            item = self._repo.get(item_id)
        except ItemNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return ItemResponse(**item.__dict__)

    def list(self, query: ItemListQuery) -> List[ItemResponse]:
        items = self._repo.list(
            offset=query.offset or 0,
            limit=query.limit,
            min_price=query.min_price,
            max_price=query.max_price,
            show_deleted=query.show_deleted,
        )
        return [ItemResponse(**item.__dict__) for item in items]

    def update(self, item_id: int, request: ItemUpdateRequest) -> ItemResponse:
        try:
            item = self._repo.update(item_id, name=request.name, price=request.price)
        except ItemNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        except ItemDeletedError:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
        return ItemResponse(**item.__dict__)

    def patch(self, item_id: int, request: ItemPatchRequest) -> ItemResponse:
        payload = request.dict(exclude_unset=True)
        if "deleted" in payload:
            # чтобы сработала валидация Pydantic -> 422
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            item = self._repo.patch(item_id, name=payload.get("name"), price=payload.get("price"))
        except ItemNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        except ItemDeletedError:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
        return ItemResponse(**item.__dict__)

    def delete(self, item_id: int) -> None:
        try:
            self._repo.delete(item_id)
        except ItemNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


class CartService:
    def __init__(self, repo: CartRepository, item_repo: ItemRepository):
        self._repo = repo
        self._item_repo = item_repo

    def create(self) -> CartCreateResponse:
        cart = self._repo.create()
        return CartCreateResponse(id=cart.id)

    def get(self, cart_id: int) -> CartResponse:
        try:
            cart = self._repo.get(cart_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        items = []
        for cart_item in cart.items_list:
            try:
                item = self._item_repo.get(cart_item.item_id)
            except ItemNotFoundError:
                continue
            items.append(
                CartItemResponse(
                    id=cart_item.item_id,
                    quantity=cart_item.quantity,
                ),
            )

        total_price = self._repo.calculate_total(cart)
        return CartResponse(id=cart.id, items=items, price=total_price)

    def list(self, query: CartListQuery) -> List[CartResponse]:
        carts = self._repo.list(
            offset=query.offset or 0,
            limit=query.limit,
            min_price=query.min_price,
            max_price=query.max_price,
            min_quantity=query.min_quantity,
            max_quantity=query.max_quantity,
        )

        response = []
        for cart in carts:
            total_price = self._repo.calculate_total(cart)
            response.append(
                CartResponse(
                    id=cart.id,
                    items=[
                        CartItemResponse(id=item.item_id, quantity=item.quantity)
                        for item in cart.items_list
                        if not self._item_repo.get(item.item_id, include_deleted=True).deleted
                    ],
                    price=total_price,
                )
            )
        return response

    def add_item(self, cart_id: int, item_id: int) -> CartResponse:
        try:
            self._repo.add_item(cart_id, item_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        except ItemNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        except ItemDeletedError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return self.get(cart_id)