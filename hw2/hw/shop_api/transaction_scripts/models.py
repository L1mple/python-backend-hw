from sqlalchemy import Column, Integer, String, Float, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from .config import Base


# Many-to-many association table between carts and items for demo
demo_cart_items_table = Table(
    "demo_cart_items",
    Base.metadata,
    Column(
        "cart_id", Integer, ForeignKey("demo_carts.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "item_id", Integer, ForeignKey("demo_items.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("quantity", Integer, nullable=False, default=1),
)


class DemoItem(Base):
    """Demonstration model of a shop item"""
    __tablename__ = "demo_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)

    # Relationship with carts (via association table)
    carts = relationship(
        "DemoCart", secondary=demo_cart_items_table, back_populates="items"
    )

    def __repr__(self):
        return f"<DemoItem(id={self.id}, name={self.name}, price={self.price}, deleted={self.deleted})>"


class DemoCart(Base):
    """Demonstration model of a shopping cart"""
    __tablename__ = "demo_carts"

    id = Column(Integer, primary_key=True)
    price = Column(Float, default=0.0, nullable=False)

    # Relationship with items (via association table)
    items = relationship(
        "DemoItem", secondary=demo_cart_items_table, back_populates="carts"
    )

    def __repr__(self):
        return f"<DemoCart(id={self.id}, price={self.price})>"
