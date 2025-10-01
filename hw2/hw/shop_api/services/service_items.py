from ..database import Database
from ..factory import ItemCreate
from fastapi import Response, HTTPException
from http import HTTPStatus
from typing import List, Optional
from pydantic import Field
import json


class ItemService:
    def __init__(self, database: Database):
        self.db = database
    
    def create_item(self, item: ItemCreate) -> dict:
        item_id = self.db.get_next_item_id()
        
        self.db.items[item_id] = {
            "id": item_id,
            "name": item.name,
            "price": item.price,
            "deleted": False
        }
        response = Response(
            content=json.dumps(self.db.items[item_id]),
            status_code=HTTPStatus.CREATED,
            media_type="application/json",
            headers={}
        )
        return response
    
    def get_item(self, item_id: int) -> dict:
        if item_id not in self.db.items or self.db.items[item_id]["deleted"]:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
            
        return self.db.items[item_id]
    
    def list_items(
        self,
        offset: int,
        limit: int,
        min_price: Optional[float],
        max_price: Optional[float],
        show_deleted: bool
    ) -> List[dict]:
        filtered_items = []
        
        for item in self.db.items.values():
            if not show_deleted and item["deleted"]:
                continue
            
            price = item["price"]
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
                
            filtered_items.append(item)
        
        filtered_items.sort(key=lambda x: x["id"])
        return filtered_items[offset:offset + limit]
    
    def replace_item(self, item_id: int, item: ItemCreate) -> dict:
        if item_id not in self.db.items:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

        if self.db.items[item_id]["deleted"]:
            raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted")
        
        self.db.items[item_id].update({
            "name": item.name,
            "price": item.price
        })
        return self.db.items[item_id]
    
    def update_item(self, item_id: int, item: dict) -> dict:
        if item_id not in self.db.items:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

        if self.db.items[item_id]["deleted"]:
            raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted")


        allowed_fields = {'name', 'price'}
        extra_fields = set(item.keys()) - allowed_fields

        if extra_fields:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=f"Extra fields not allowed: {extra_fields}"
            )

        self.db.items[item_id]['name'] = item['name'] if 'name' in item else self.db.items[item_id]['name']
        self.db.items[item_id]['price'] = item['price'] if 'price' in item else self.db.items[item_id]['price']
        return self.db.items[item_id]
    
    def delete_item(self, item_id: int) -> dict:
        if item_id not in self.db.items:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
            
        self.db.items[item_id]["deleted"] = True

        return {"message": "Item deleted successfully"}
