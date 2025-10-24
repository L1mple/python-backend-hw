from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_
from .. import models, factory
from fastapi import HTTPException
from http import HTTPStatus
from typing import List, Optional

class ItemService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_item(self, item: factory.ItemCreate) -> factory.ItemResponse:
        try:
            db_item = models.Item(
                name=item.name,
                price=item.price
            )
            self.db.add(db_item)
            self.db.commit()
            self.db.refresh(db_item)
            return self._item_to_response(db_item)
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Database integrity error - possible duplicate or constraint violation"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    def get_item(self, item_id: int) -> factory.ItemResponse:
        try:
            item = self.db.query(models.Item).filter(
                models.Item.id == item_id
            ).first()
            
            if not item or item.deleted:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, 
                    detail="Item not found"
                )
            return self._item_to_response(item)
            
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error while fetching item"
            )
    
    def list_items(
        self,
        offset: int,
        limit: int,
        min_price: Optional[float],
        max_price: Optional[float],
        show_deleted: bool
    ) -> List[factory.ItemResponse]:
        try:
            query = self.db.query(models.Item)
            
            if not show_deleted:
                query = query.filter(models.Item.deleted == False)
            
            if min_price is not None:
                query = query.filter(models.Item.price >= min_price)
            
            if max_price is not None:
                query = query.filter(models.Item.price <= max_price)
            
            items = query.offset(offset).limit(limit).all()
            return [self._item_to_response(item) for item in items]
            
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error while listing items"
            )
    
    def replace_item(self, item_id: int, item: factory.ItemCreate) -> factory.ItemResponse:
        try:
            db_item = self.get_item_orm(item_id)
            
            db_item.name = item.name
            db_item.price = item.price
            
            self.db.commit()
            self.db.refresh(db_item)
            return self._item_to_response(db_item)
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Invalid data - constraint violation"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error while updating item"
            )
    
    def update_item(self, item_id: int, item_data: dict) -> factory.ItemResponse:
        try:
            db_item = self.get_item_orm(item_id)
            
            allowed_fields = {'name', 'price'}
            extra_fields = set(item_data.keys()) - allowed_fields

            if extra_fields:
                raise HTTPException(
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    detail=f"Extra fields not allowed: {extra_fields}"
                )

            for field, value in item_data.items():
                setattr(db_item, field, value)
            
            self.db.commit()
            self.db.refresh(db_item)
            return self._item_to_response(db_item)
            
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Invalid data - constraint violation"
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error while updating item"
            )
    
    def delete_item(self, item_id: int) -> dict:
        try:
            db_item = self.get_item_orm(item_id)
            db_item.deleted = True
            self.db.commit()
            return {"message": "Item deleted successfully"}
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Database error while deleting item"
            )

    def get_item_orm(self, item_id: int) -> models.Item:
        """Внутренний метод для получения ORM объекта (без преобразования в схему)"""
        item = self.db.query(models.Item).filter(
            models.Item.id == item_id
        ).first()
        
        if not item or item.deleted:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, 
                detail="Item not found"
            )
        return item

    def _item_to_response(self, item: models.Item) -> factory.ItemResponse:
        """Преобразует ORM объект Item в Pydantic схему ItemResponse"""
        return factory.ItemResponse(
            id=item.id,
            name=item.name,
            price=item.price,
            deleted=item.deleted,
            created_at=item.created_at
        )
