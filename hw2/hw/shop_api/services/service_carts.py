from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import and_
from .. import models, factory
from fastapi import HTTPException
from http import HTTPStatus
from typing import List, Optional

class CartService:
    def __init__(self, db: Session):
        self.db = db

    def create_cart(self) -> factory.CartResponse:
        cart = models.Cart()
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return factory.CartResponse(
            id=cart.id,
            items=[],
            price=cart.price,
            created_at=cart.created_at
        )
    
    def get_cart(self, cart_id: int) -> factory.CartResponse:
        cart = self.db.query(models.Cart).filter(
            models.Cart.id == cart_id
        ).first()
        
        if not cart:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, 
                detail="Cart not found"
            )
        
        # Преобразуем ORM объект в Pydantic схему
        return self._cart_to_response(cart)

    def add_to_cart(self, cart_id: int, item_id: int) -> factory.CartResponse:
        # Проверяем существование корзины
        cart = self.db.query(models.Cart).filter(
            models.Cart.id == cart_id
        ).first()
        
        if not cart:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, 
                detail="Cart not found"
            )
            
        # Проверяем существование товара
        item = self.db.query(models.Item).filter(
            and_(
                models.Item.id == item_id,
                models.Item.deleted == False
            )
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, 
                detail="Item not found or deleted"
            )

        # Проверяем есть ли товар уже в корзине
        cart_item = self.db.query(models.CartItem).filter(
            and_(
                models.CartItem.cart_id == cart_id,
                models.CartItem.item_id == item_id
            )
        ).first()
        
        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = models.CartItem(
                cart_id=cart_id,
                item_id=item_id,
                quantity=1
            )
            self.db.add(cart_item)
        
        self._update_cart_price(cart)
        self.db.commit()
        
        # Возвращаем обновленную корзину
        return self._cart_to_response(cart)

    def _update_cart_price(self, cart: models.Cart) -> None:
        total_price = self.db.query(
            func.sum(models.CartItem.quantity * models.Item.price)
        ).select_from(models.CartItem).join(
            models.Item, models.CartItem.item_id == models.Item.id
        ).filter(
            and_(
                models.CartItem.cart_id == cart.id,
                models.Item.deleted == False
            )
        ).scalar() or 0.0
        
        cart.price = total_price

    def _cart_to_response(self, cart: models.Cart) -> factory.CartResponse:
        """Преобразует ORM объект Cart в Pydantic схему CartResponse"""
        cart_items = []
        
        for cart_item in cart.items:
            # Вычисляем availability для каждого товара
            item_available = (
                cart_item.item is not None and 
                not cart_item.item.deleted
            )
            
            # Создаем CartItemResponse для каждого товара
            cart_items.append(factory.CartItem(
                id=cart_item.item_id,
                name=cart_item.item.name if cart_item.item else "Unknown Item",
                quantity=cart_item.quantity,
                available=item_available
            ))
        
        # Создаем финальный ответ
        return factory.CartResponse(
            id=cart.id,
            items=cart_items,
            price=cart.price,
            created_at=cart.created_at
        )

    def list_carts(
        self,
        offset: int,
        limit: int,
        min_price: Optional[float],
        max_price: Optional[float],
        min_quantity: Optional[int],
        max_quantity: Optional[int]
    ) -> List[factory.CartResponse]:
        query = self.db.query(models.Cart)
        
        # Subquery for cart quantities
        quantity_subquery = self.db.query(
            models.CartItem.cart_id,
            func.sum(models.CartItem.quantity).label('total_quantity')
        ).group_by(models.CartItem.cart_id).subquery()
        
        query = query.outerjoin(
            quantity_subquery, 
            models.Cart.id == quantity_subquery.c.cart_id
        )
        
        if min_price is not None:
            query = query.filter(models.Cart.price >= min_price)
        
        if max_price is not None:
            query = query.filter(models.Cart.price <= max_price)
        
        if min_quantity is not None:
            query = query.filter(
                quantity_subquery.c.total_quantity >= min_quantity
            )
        
        if max_quantity is not None:
            query = query.filter(
                quantity_subquery.c.total_quantity <= max_quantity
            )
        
        # Преобразуем все ORM объекты в Pydantic схемы
        carts = query.offset(offset).limit(limit).all()
        return [self._cart_to_response(cart) for cart in carts]