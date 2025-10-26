from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from .models import User, Product, Order
from .schemas import UserCreate, ProductCreate, OrderCreate


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name,
        age=user.age
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: UserCreate) -> Optional[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        for field, value in user_update.model_dump().items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None
) -> List[Product]:
    query = db.query(Product)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is not None:
        query = query.filter(Product.in_stock == in_stock)

    return query.offset(skip).limit(limit).all()


def create_product(db: Session, product: ProductCreate) -> Product:
    db_product = Product(
        name=product.name,
        price=product.price,
        description=product.description,
        in_stock=product.in_stock
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product_update: ProductCreate) -> Optional[Product]:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        for field, value in product_update.model_dump().items():
            setattr(db_product, field, value)
        db.commit()
        db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int) -> bool:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False


def get_order(db: Session, order_id: int) -> Optional[Order]:
    return db.query(Order).filter(Order.id == order_id).first()


def get_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    product_id: Optional[int] = None,
    status: Optional[str] = None
) -> List[Order]:
    query = db.query(Order)

    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    if product_id is not None:
        query = query.filter(Order.product_id == product_id)
    if status is not None:
        query = query.filter(Order.status == status)

    return query.offset(skip).limit(limit).all()


def create_order(db: Session, order: OrderCreate) -> Order:
    product = get_product(db, order.product_id)
    if not product:
        raise ValueError("Product not found")

    total_price = product.price * order.quantity

    db_order = Order(
        user_id=order.user_id,
        product_id=order.product_id,
        quantity=order.quantity,
        total_price=total_price,
        status=order.status
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def update_order(db: Session, order_id: int, order_update: OrderCreate) -> Optional[Order]:
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        if order_update.product_id != db_order.product_id or order_update.quantity != db_order.quantity:
            product = get_product(db, order_update.product_id)
            if not product:
                raise ValueError("Product not found")
            db_order.total_price = product.price * order_update.quantity

        for field, value in order_update.model_dump().items():
            if field not in ['user_id', 'product_id', 'quantity']:
                setattr(db_order, field, value)

        db.commit()
        db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: int) -> bool:
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        db.delete(db_order)
        db.commit()
        return True
    return False
