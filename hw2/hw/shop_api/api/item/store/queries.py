from sqlalchemy.orm import Session
from typing import Iterable
from decimal import Decimal
from shop_api.database import get_db
from shop_api.database.models import Product
from shop_api.database.crud import (
    get_product, get_products, create_product, update_product, delete_product
)
from .models import ItemEntity, ItemInfo, PatchItemInfo


def add(info: ItemInfo) -> ItemEntity:
    from shop_api.database.schemas import ProductCreate

    product_create = ProductCreate(
        name=info.name,
        price=float(info.price),
        in_stock=not info.deleted
    )

    with next(get_db()) as db:
        db_product = create_product(db, product_create)
        return ItemEntity.from_product(db_product)


def delete(id: int) -> None:
    with next(get_db()) as db:
        product = get_product(db, id)
        if product:
            product.in_stock = False
            db.commit()


def get_one(id: int) -> ItemEntity | None:
    with next(get_db()) as db:
        product = get_product(db, id)
        return ItemEntity.from_product(product) if product else None


def get_list(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False
) -> Iterable[ItemEntity]:
    with next(get_db()) as db:
        min_price_decimal = Decimal(str(min_price)) if min_price is not None else None
        max_price_decimal = Decimal(str(max_price)) if max_price is not None else None

        products = get_products(
            db=db,
            skip=offset,
            limit=limit,
            min_price=min_price_decimal,
            max_price=max_price_decimal,
            in_stock=None if show_deleted else True
        )

        return [ItemEntity.from_product(product) for product in products]


def update(id: int, info: ItemInfo) -> ItemEntity | None:
    from shop_api.database.schemas import ProductCreate

    product_update = ProductCreate(
        name=info.name,
        price=float(info.price),
        in_stock=not info.deleted
    )

    with next(get_db()) as db:
        updated_product = update_product(db, id, product_update)
        return ItemEntity.from_product(updated_product) if updated_product else None


def upsert(id: int, info: ItemInfo) -> ItemEntity:
    from shop_api.database.schemas import ProductCreate

    product_update = ProductCreate(
        name=info.name,
        price=float(info.price),
        in_stock=not info.deleted
    )

    with next(get_db()) as db:
        updated_product = update_product(db, id, product_update)
        if updated_product:
            return ItemEntity.from_product(updated_product)

        db_product = create_product(db, product_update)
        return ItemEntity.from_product(db_product)


def patch(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    with next(get_db()) as db:
        product = get_product(db, id)
        if not product:
            return None

        if patch_info.name is not None:
            product.name = patch_info.name
        if patch_info.price is not None:
            product.price = patch_info.price

        db.commit()
        db.refresh(product)
        return ItemEntity.from_product(product)
