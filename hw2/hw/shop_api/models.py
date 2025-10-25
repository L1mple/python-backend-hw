from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

cart_items = Table(
    'cart_items',
    Base.metadata,
    Column('cart_id', Integer, ForeignKey('carts.id', ondelete='CASCADE'), primary_key=True),
    Column('item_id', Integer, ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
    Column('quantity', Integer, nullable=False, default=1),
    extend_existing=True
)


class ItemModel(Base):

    __tablename__ = "items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False, index=True)
    carts = relationship(
        "CartModel",
        secondary=cart_items,
        back_populates="items",
        overlaps="items,carts"
    )

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', price={self.price}, deleted={self.deleted})>"


class CartModel(Base):

    __tablename__ = "carts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    items = relationship(
        "ItemModel",
        secondary=cart_items, 
        back_populates="carts",
        overlaps="items,carts"
    )

    def __repr__(self):
        return f"<Cart(id={self.id}, items_count={len(self.items)})>"

def get_cart_item_quantity(db, cart_id: int, item_id: int) -> int:

    result = db.execute(
        cart_items.select().where(
            cart_items.c.cart_id == cart_id,
            cart_items.c.item_id == item_id
        )
    ).fetchone()
    
    return result.quantity if result else 0


def set_cart_item_quantity(db, cart_id: int, item_id: int, quantity: int):

    existing = db.execute(
        cart_items.select().where(
            cart_items.c.cart_id == cart_id,
            cart_items.c.item_id == item_id
        )
    ).fetchone()
    
    if existing:
        db.execute(
            cart_items.update().where(
                cart_items.c.cart_id == cart_id,
                cart_items.c.item_id == item_id
            ).values(quantity=quantity)
        )
    else:
        db.execute(
            cart_items.insert().values(
                cart_id=cart_id,
                item_id=item_id,
                quantity=quantity
            )
        )
    
    db.commit()


def get_cart_items_with_quantity(db, cart_id: int):
    result = db.execute(
        cart_items.select().where(cart_items.c.cart_id == cart_id)
    ).fetchall()
    
    items_with_quantity = []
    for row in result:
        item = db.query(ItemModel).filter(ItemModel.id == row.item_id).first()
        if item:
            items_with_quantity.append((item, row.quantity))
    
    return items_with_quantity