from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import CRUDBase
from ..models import ItemModel
from src.schemas import ItemCreate


class CRUDItem(CRUDBase[ItemModel, ItemCreate]):

    async def get_items_with_filters(
            self,
            db: AsyncSession,
            offset: int,
            limit: int,
            min_price: Optional[float],
            max_price: Optional[float],
            show_deleted: bool,
    ) -> List[ItemModel]:

        query = select(ItemModel)
        query = query.where(ItemModel.deleted.is_(show_deleted))

        if min_price is not None:
            query = query.where(ItemModel.price >= min_price)
        if max_price is not None:
            query = query.where(ItemModel.price <= max_price)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


    async def soft_delete(
            self,
            db: AsyncSession,
            *,
            id: UUID,
    ) -> Optional[ItemModel]:

        obj = await self.get(db, id)
        if obj is None:
            return None

        obj.deleted = True
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj


crud_item = CRUDItem(ItemModel)