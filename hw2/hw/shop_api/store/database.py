from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DECIMAL,
    create_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

Base = declarative_base()


class ItemOrm(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    deleted = Column(Boolean, default=False)

    # One-to-many: an Item has a collection of CartItem rows
    cart_items = relationship("CartItemOrm", back_populates="item")


class CartItemOrm(Base):
    __tablename__ = "cart_items"
    # Composite primary key: cart_id and item_id
    cart_id = Column(
        Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True
    )
    item_id = Column(Integer, ForeignKey("items.id"), primary_key=True)

    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    available = Column(Boolean, default=True)

    # Many-to-one: each CartItem refers to exactly one Cart
    cart = relationship("CartOrm", back_populates="items")
    # Many-to-one: each CartItem refers to exactly one Item
    item = relationship("ItemOrm", back_populates="cart_items")


class CartOrm(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # One-to-many: a Cart has a collection of CartItem rows
    items = relationship(
        "CartItemOrm",
        back_populates="cart",
        cascade="all, delete-orphan",  # optional but common for parent/child
        lazy="selectin",  # efficient loading for collections
        order_by="CartItemOrm.item_id",  # optional: stable ordering
    )


# Database connection setup
import os

# Get database connection details from environment variables
DB_USER = os.getenv("MYSQL_USER", "shop_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "shop_password")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "shop_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

print(f"🔌 Connecting to database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Connection pool settings for production
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # Number of connections to keep open
    max_overflow=20,  # Max connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Test connections before using
    echo=True,  # Set to True for SQL query logging (debug)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def drop_tables():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


def get_db():
    """FastAPI dependency for database sessions"""
    db = get_session()
    try:
        yield db
        db.commit()  # Commit transaction if no errors
    except Exception:
        db.rollback()  # Rollback on errors
        raise
    finally:
        db.close()
