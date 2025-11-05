from typing import List, Optional
from sqlalchemy import select, update, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .db import AsyncSessionLocal, Item as ItemModel, Cart as CartModel, CartItem as CartItemModel
from .schemas import ItemCreate, Item, Cart, CartItem


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


class ItemStorage:
    @staticmethod
    async def create(item: ItemCreate) -> Item:
        async with AsyncSessionLocal() as session:
            db_item = ItemModel(name=item.name, price=item.price)
            session.add(db_item)
            await session.commit()
            await session.refresh(db_item)
            return Item.from_orm(db_item)

    @staticmethod
    async def get(item_id: int) -> Optional[Item]:
        async with AsyncSessionLocal() as session:
            result = await session.get(ItemModel, item_id)
            if not result:
                return None
            return Item.from_orm(result)

    @staticmethod
    async def get_all() -> List[Item]:
        async with AsyncSessionLocal() as session:
            q = await session.execute(select(ItemModel))
            items = q.scalars().all()
            return [Item.from_orm(i) for i in items]

    @staticmethod
    async def update(item: Item) -> None:
        async with AsyncSessionLocal() as session:
            await session.merge(ItemModel(id=item.id, name=item.name, price=item.price, deleted=item.deleted))
            await session.commit()

    @staticmethod
    async def delete(item_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            db_item = await session.get(ItemModel, item_id)
            if not db_item:
                return False
            db_item.deleted = True
            await session.commit()
            return True

    @staticmethod
    async def exists(item_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            db_item = await session.get(ItemModel, item_id)
            return db_item is not None


class CartStorage:
    @staticmethod
    async def create() -> int:
        async with AsyncSessionLocal() as session:
            cart = CartModel(price=0.0)
            session.add(cart)
            await session.commit()
            await session.refresh(cart)
            return cart.id

    @staticmethod
    async def get(cart_id: int) -> Optional[Cart]:
        async with AsyncSessionLocal() as session:
            cart = await session.get(CartModel, cart_id)
            if not cart:
                return None
            # collect cart items
            q = await session.execute(select(CartItemModel).where(CartItemModel.cart_id == cart_id))
            cart_items = q.scalars().all()
            items = []
            for ci in cart_items:
                item = await session.get(ItemModel, ci.item_id)
                items.append(CartItem(id=ci.item_id, name=item.name, quantity=ci.quantity, available=not item.deleted))
            return Cart(id=cart.id, items=items, price=cart.price)

    @staticmethod
    async def get_all() -> List[Cart]:
        async with AsyncSessionLocal() as session:
            q = await session.execute(select(CartModel))
            carts = q.scalars().all()
            result = []
            for cart in carts:
                q_items = await session.execute(select(CartItemModel).where(CartItemModel.cart_id == cart.id))
                cart_items = q_items.scalars().all()
                items = []
                for ci in cart_items:
                    item = await session.get(ItemModel, ci.item_id)
                    items.append(CartItem(id=ci.item_id, name=item.name, quantity=ci.quantity, available=not item.deleted))
                result.append(Cart(id=cart.id, items=items, price=cart.price))
            return result

    @staticmethod
    async def update(cart: Cart) -> None:
        async with AsyncSessionLocal() as session:
            db_cart = await session.get(CartModel, cart.id)
            if not db_cart:
                return
            db_cart.price = cart.price
            await session.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart.id))
            for ci in cart.items:
                session.add(CartItemModel(cart_id=cart.id, item_id=ci.id, quantity=ci.quantity))
            await session.commit()
