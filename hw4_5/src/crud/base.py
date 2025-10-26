from typing import TypeVar, Generic, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Result
from pydantic import BaseModel
from uuid import UUID

from ..models import Base



ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)



class CRUDBase(Generic[ModelType, CreateSchemaType]):
    def __init__(
            self,
            model: ModelType
    ):
        self.model = model

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Optional[CreateSchemaType] = None,
        **kwargs: Any
    ) -> ModelType:

        if obj_in is not None:
            obj_data = obj_in.model_dump()
        else:
            obj_data = kwargs

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


    async def get(
            self,
            db: AsyncSession,
            id: UUID
    ) -> Optional[ModelType]:

        query = select(self.model).where(self.model.id == id)
        result: Result = await db.execute(query)
        return result.scalars().first()


    async def update(
        self,
        db: AsyncSession,
        *,
        id: UUID,
        obj_in: dict | BaseModel,
        skip_deleted_check: bool = False  # если модель не имеет deleted
    ) -> Optional[ModelType]:

        db_obj = await self.get(db, id)
        if not db_obj:
            return None

        if hasattr(db_obj, 'deleted') and not skip_deleted_check:
            if db_obj.deleted:
                return None

        if isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)  # только переданные поля
        else:
            update_data = obj_in

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
