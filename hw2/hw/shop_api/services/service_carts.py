from ..database import Database
from fastapi import Response, HTTPException
from http import HTTPStatus
from typing import List, Optional
from pydantic import Field
import json


class CartService:
    def __init__(self, database: Database):
        self.db = database

    def create_cart(self) -> dict:
        cart_id = self.db.get_next_cart_id()

        self.db.carts[cart_id] = {
            'id': cart_id,
            'items': [],
            'price': 0.0
        }
        response = Response(
            content=json.dumps(self.db.carts[cart_id]),
            status_code=HTTPStatus.CREATED,
            media_type="application/json",
            headers={}
        )
        response.headers["Location"] = f"/cart/{cart_id}"
        return response
    
    def get_cart(self, cart_id: int) -> dict:
        if cart_id not in self.db.carts:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

        cart = self.db.carts[cart_id]
        
        self._update_cart_items_availability(cart)
        self._calculate_cart_price(cart)

        return cart


    def add_to_cart(self, cart_id: int, item_id: int) -> None:
        if cart_id not in self.db.carts:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
        if item_id not in self.db.items:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found or deleted")
        
        if self.db.items[item_id]["deleted"]:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found or deleted")


        cart = self.db.carts[cart_id]
        item_data = self.db.items[item_id]
        
        # Проверяем, есть ли товар уже в корзине
        existing_item = None
        for cart_item in cart["items"]:
            if cart_item["id"] == item_id:
                existing_item = cart_item
                break
        
        if existing_item:
            existing_item["quantity"] += 1
        else:
            # Добавляем новый товар
            cart["items"].append({
                "id": item_id,
                "name": item_data["name"],
                "quantity": 1,
                "available": True
            })
        
        self._update_cart_items_availability(cart)
        self._calculate_cart_price(cart)
        return cart


    def _update_cart_items_availability(self, cart: dict) -> None:
        """Обновляет поле available для всех товаров в корзине"""
        for item in cart["items"]:
            item_id = item["id"]
            if item_id in self.db.items and not self.db.items[item_id]["deleted"]:
                item["available"] = True
                item["name"] = self.db.items[item_id]["name"]
            else:
                item["available"] = False
    
    def _calculate_cart_price(self, cart: dict) -> None:
        """Пересчитывает общую стоимость корзины"""
        total = 0.0
        for item in cart["items"]:
            if item["available"] and item["id"] in self.db.items:
                total += self.db.items[item["id"]]["price"] * item["quantity"]
        cart["price"] = total

    def list_carts(
        self,
        offset: int,
        limit: int,
        min_price: Optional[float],
        max_price: Optional[float],
        min_quantity: Optional[int],
        max_quantity: Optional[int]
    ) -> List[dict]:
        filtered_carts = []
        
        for cart in self.db.carts.values():
            # Обновляем availability и цену
            self._update_cart_items_availability(cart)
            self._calculate_cart_price(cart)
            
            total_quantity = sum(item["quantity"] for item in cart["items"])
            price = cart["price"]
            
            # Фильтрация по цене
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            
            # Фильтрация по количеству товаров
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue
                
            filtered_carts.append(cart)
        
        filtered_carts.sort(key=lambda x: x["id"])
        return filtered_carts[offset:offset + limit]
        