from typing import Iterable
from sqlalchemy import func
from sqlalchemy.orm import Session

from shop_api.store.models import (
    Item,
    Cart,
    CartItem
)


def add_item(db: Session, orm_item: Item) -> Item:
    db.add(orm_item)
    db.commit()
    db.refresh(orm_item)
    return orm_item


def delete_item(db: Session, id: int) -> None:
    orm_item = get_item(db, id)
    if orm_item != None:
        orm_item.deleted = True
        db.commit()


def get_item(db: Session, id: int) -> Item | None:
    return db.query(Item).filter(Item.id == id).first()


def get_items(
        db: Session,
        offset: int = 0, 
        limit: int = 10, 
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False
    ) -> Iterable[Item]:

    # Начинаем построение запроса
    query = db.query(Item)
    
    # Фильтр по минимальной цене
    if min_price != None:
        query = query.filter(Item.price >= min_price)
    
    # Фильтр по максимальной цене
    if max_price != None:
        query = query.filter(Item.price <= max_price)
    
    # Фильтр по удаленным товарам
    if not show_deleted:
        query = query.filter(Item.deleted == False)
    # Если show_deleted=True, показываем все товары включая удаленные
    
    # Применяем пагинацию
    items = query.offset(offset).limit(limit).all()
    
    return items


def update_item(db: Session, id: int, name: str, price: float, deleted: bool) -> Item | None:
    orm_item = get_item(db, id)

    if orm_item == None:
        return None

    orm_item.name = name
    orm_item.price = price
    orm_item.deleted = deleted

    db.commit()
    db.refresh(orm_item)

    return orm_item


# def upsert_item(id: int, info: ItemInfo) -> ItemEntity:
#     _items_data[id] = info

#     return ItemEntity(id=id, info=info)


def patch_item(db: Session, id: int, name: str | None, price: float | None) -> Item | None:
    orm_item = get_item(db, id)

    if orm_item == None:
        return None
    
    if name is not None:
        orm_item.name = name

    if price is not None:
        orm_item.price = price
    
    db.commit()
    db.refresh(orm_item)
    return orm_item


def get_carts(
        db: Session,
        offset: int = 0, 
        limit: int = 10, 
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None
    ) -> Iterable[Cart]:

    query = db.query(Cart)
    
    # Создаем подзапросы для цены и количества
    cart_stats_subquery = (
        db.query(
            CartItem.cart_id,
            func.sum(CartItem.quantity * Item.price).label('total_price'),
            func.sum(CartItem.quantity).label('total_quantity')
        )
        .join(Item, CartItem.item_id == Item.id)
        .group_by(CartItem.cart_id)
        .subquery()
    )
    
    # Присоединяем подзапрос к основному запросу
    query = query.join(cart_stats_subquery, Cart.id == cart_stats_subquery.c.cart_id)
    
    # Фильтрация по цене
    if min_price is not None:
        query = query.filter(cart_stats_subquery.c.total_price >= min_price)
    
    if max_price is not None:
        query = query.filter(cart_stats_subquery.c.total_price <= max_price)
    
    # Фильтрация по количеству
    if min_quantity is not None:
        query = query.filter(cart_stats_subquery.c.total_quantity >= min_quantity)
    
    if max_quantity is not None:
        query = query.filter(cart_stats_subquery.c.total_quantity <= max_quantity)
    
    # Применяем пагинацию
    carts = query.order_by(Cart.id).offset(offset).limit(limit).all()
    
    return carts



def get_cart(db: Session, id: int) -> Cart | None:
    return db.query(Cart).filter(Cart.id == id).first()


def add_cart(db: Session) -> Cart:
    orm_cart = Cart()
    db.add(orm_cart)
    db.commit()
    db.refresh(orm_cart)
    return orm_cart


def add_item_to_cart(db: Session, cart: Cart, item: Item) -> Cart:
    
    # Проверяем, есть ли уже этот товар в корзине
    existing_cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.item_id == item.id
    ).first()
    
    if existing_cart_item:
        # Если товар уже есть - увеличиваем количество
        existing_cart_item.quantity += 1
        cart_item = existing_cart_item
    else:
        # Если товара нет - создаем новую запись
        cart_item = CartItem(cart_id=cart.id, item_id=item.id, quantity=1)
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart)
    
    return cart