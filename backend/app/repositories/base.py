from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository for generic CRUD operations."""

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get an entity by ID."""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self) -> List[T]:
        """Get all entities."""
        result = await self.db.execute(select(self.model))
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        """Create a new entity."""
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: int, obj_data: dict) -> Optional[T]:
        """Update an entity."""
        obj = await self.get_by_id(id)
        if obj:
            for key, value in obj_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """Delete an entity."""
        obj = await self.get_by_id(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
            return True
        return False
