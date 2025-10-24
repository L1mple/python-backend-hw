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
        # print(f"DEBUG: Cart {cart_id} price from DB: {cart.price}")

        self._update_cart_price(cart)
        self.db.commit()
        self.db.refresh(cart)
    
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
        self.db.refresh(cart)
        return self._cart_to_response(cart)
    
    def _update_cart_price(self, cart: models.Cart) -> None:
        total_price = 0.0
                
        cart_items = self.db.query(models.CartItem).filter(
            models.CartItem.cart_id == cart.id
        ).join(models.Item).all()


        for i, cart_item in enumerate(cart_items):
            # print(f"DEBUG: CartItem {i}: id={cart_item.id}, item_id={cart_item.item_id}, quantity={cart_item.quantity}")
            
            if cart_item.item:
                item_price = cart_item.item.price
                quantity = cart_item.quantity
                item_total = item_price * quantity
                
                # print(f"DEBUG:   Item {cart_item.item_id} - name: {cart_item.item.name}, price: {item_price}, quantity: {quantity}, total: {item_total}")
                
                total_price += item_total
            # else:
            #     print(f"DEBUG:   CartItem {cart_item.id} has no associated item")
        
        # print(f"DEBUG: Total cart price: {total_price}")
        cart.price = total_price
        

    def _cart_to_response(self, cart: models.Cart) -> factory.CartResponse:
        """Преобразует ORM объект Cart в Pydantic схему CartResponse"""
        cart_items = []
        
        cart_items_db = self.db.query(models.CartItem).filter(
            models.CartItem.cart_id == cart.id
        ).join(models.Item).all()
        
        # print(f"DEBUG: _cart_to_response - Found {len(cart_items_db)} cart_items in DB")
        
        for cart_item in cart_items_db:
            # Вычисляем availability для каждого товара
            item_available = (
                cart_item.item is not None and 
                not cart_item.item.deleted
            )
            
            # print(f"DEBUG: _cart_to_response - item_id: {cart_item.item_id}, quantity: {cart_item.quantity}, price: {cart_item.item.price if cart_item.item else 'N/A'}")
            
            cart_items.append(factory.CartItem(
                id=cart_item.item_id,
                name=cart_item.item.name if cart_item.item else "Unknown Item",
                quantity=cart_item.quantity,
                available=item_available
            ))
        
        response = factory.CartResponse(
            id=cart.id,
            items=cart_items,
            price=cart.price,
            created_at=cart.created_at
        )
        
        # print(f"DEBUG: _cart_to_response - Final response price: {response.price}")
        
        return response

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