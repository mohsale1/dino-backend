"""
BaseRepository — async SQLAlchemy 2.x generic CRUD layer for dino-system.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import asc, desc, func, literal, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.Base import Base
from src.base.BaseModel import row_to_dict


class BaseRepository:
    """Generic async repository backed by SQLAlchemy 2.x + asyncpg."""

    def __init__(self, model: Type[Base], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_soft_delete_filter(self, stmt, include_deleted: bool):
        """Append is_active = true filter when the model supports it."""
        if not include_deleted and hasattr(self.model, "is_active"):
            stmt = stmt.where(self.model.is_active == True)  # noqa: E712
        return stmt

    def _apply_filters(self, stmt, filters: Optional[Dict[str, Any]]):
        """Append equality filters for each key/value pair."""
        if filters:
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    stmt = stmt.where(column == value)
        return stmt

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new row and return it as a dict."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple rows and return them as dicts."""
        instances = [self.model(**item) for item in items]
        self.db.add_all(instances)
        await self.db.flush()
        for instance in instances:
            await self.db.refresh(instance)
        return [row_to_dict(i) for i in instances]

    async def update(self, entity_id: Any, data: Dict[str, Any]) -> bool:
        """
        Update a row by primary key.
        Sets updated_at automatically when the column exists.
        Returns True if a row was matched, False otherwise.
        """
        if hasattr(self.model, "updated_at"):
            data = {**data, "updated_at": datetime.now(timezone.utc)}

        pk_col = self.model.__table__.primary_key.columns.values()[0]
        stmt = (
            update(self.model)
            .where(pk_col == entity_id)
            .values(**data)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete(self, entity_id: Any) -> bool:
        """Mark a row as deleted without removing it from the database."""
        return await self.update(entity_id, {"is_active": False})

    async def restore(self, entity_id: Any) -> bool:
        """Restore a previously soft-deleted row."""
        return await self.update(entity_id, {"is_active": True})

    async def delete(self, entity_id: Any) -> bool:
        """
        Hard-delete a row by primary key.
        NOT RECOMMENDED — prefer soft_delete() instead.
        """
        pk_col = self.model.__table__.primary_key.columns.values()[0]
        stmt = (
            delete(self.model)
            .where(pk_col == entity_id)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(
        self, entity_id: Any, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row by primary key. Returns None if not found."""
        pk_col = self.model.__table__.primary_key.columns.values()[0]
        stmt = select(self.model).where(pk_col == entity_id)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_field(
        self, field: str, value: Any, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Fetch the first row where *field* equals *value*."""
        column = getattr(self.model, field, None)
        if column is None:
            raise ValueError(f"Model '{self.model.__name__}' has no field '{field}'")
        stmt = select(self.model).where(column == value)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        stmt = stmt.limit(1)
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_email(
        self, email: str, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Convenience wrapper around get_by_field for the email column."""
        return await self.get_by_field("email", email, include_deleted)

    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> List[Dict[str, Any]]:
        """Return all rows matching the given filters."""
        stmt = select(self.model)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        stmt = self._apply_filters(stmt, filters)

        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(
                    asc(column) if order_direction.lower() == "asc" else desc(column)
                )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return a page of rows together with the total count and total pages.

        Uses two SQL queries:
          1. COUNT(*) for the total
          2. SELECT … LIMIT/OFFSET for the page

        Returns: (items, total_count, total_pages)
        """
        # --- COUNT query ---
        count_stmt = select(func.count()).select_from(self.model)
        count_stmt = self._apply_soft_delete_filter(count_stmt, include_deleted)
        count_stmt = self._apply_filters(count_stmt, filters)
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        # --- Data query ---
        stmt = select(self.model)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        stmt = self._apply_filters(stmt, filters)

        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(
                    asc(column) if order_direction.lower() == "asc" else desc(column)
                )

        stmt = stmt.limit(page_size).offset(offset)
        result = await self.db.execute(stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total_count, total_pages

    # ------------------------------------------------------------------
    # Existence / count helpers
    # ------------------------------------------------------------------

    async def exists(
        self, field: str, value: Any, include_deleted: bool = False
    ) -> bool:
        """Return True if at least one row matches field == value."""
        column = getattr(self.model, field, None)
        if column is None:
            raise ValueError(f"Model '{self.model.__name__}' has no field '{field}'")
        stmt = select(literal(1)).select_from(self.model).where(column == value).limit(1)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        result = (await self.db.execute(stmt)).scalar()
        return result is not None

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the number of rows matching the given filters."""
        stmt = select(func.count()).select_from(self.model)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        stmt = self._apply_filters(stmt, filters)
        return (await self.db.execute(stmt)).scalar_one()
