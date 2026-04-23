"""
BaseRepository — async SQLAlchemy 2.x CRUD layer.

Every concrete repository inherits from this class and passes its ORM model
and the injected AsyncSession from the FastAPI get_db() dependency.

Soft-delete convention
----------------------
- is_active = True  → record is live/exists
- is_active = False → record is soft-deleted
- There is NO is_deleted column anywhere in the schema.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from sqlalchemy import and_, delete, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.Base import Base

logger = logging.getLogger(__name__)


class BaseRepository:
    """Generic async CRUD repository backed by SQLAlchemy 2.x + asyncpg."""

    def __init__(self, model: Type[Base], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_where_clauses(
        self,
        filters: Optional[Dict[str, Any]],
        include_deleted: bool,
    ) -> list:
        """Return a list of SQLAlchemy column expressions for WHERE.

        When *include_deleted* is False (the default) and the model has an
        ``is_active`` column, only active (non-deleted) rows are returned by
        appending ``is_active == True``.  Passing ``include_deleted=True``
        suppresses that guard and returns all rows regardless of is_active.

        Raises
        ------
        ValueError
            If any key in *filters* is not a mapped column on the model.
        """
        clauses = []

        if not include_deleted and hasattr(self.model, "is_active"):
            clauses.append(self.model.is_active == True)  # noqa: E712

        if filters:
            for field, value in filters.items():
                col = getattr(self.model, field, None)
                if col is None:
                    raise ValueError(
                        f"'{field}' is not a valid column on {self.model.__name__}"
                    )
                clauses.append(col == value)

        return clauses

    def _order_column(self, order_by: str, order_direction: str):
        """Resolve an order-by column expression.

        Logs a warning and falls back to ``created_at`` (then None) when
        *order_by* does not match any column on the model.
        """
        col = getattr(self.model, order_by, None)
        if col is None:
            logger.warning(
                "BaseRepository._order_column: '%s' is not a valid column on %s — "
                "falling back to 'created_at'.",
                order_by,
                self.model.__name__,
            )
            col = getattr(self.model, "created_at", None)
        if col is None:
            return None
        return col.desc() if order_direction.lower() == "desc" else col.asc()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: Dict[str, Any]) -> dict:
        """INSERT a new row and return it as a dict."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def update(
        self,
        entity_id: Union[str, int],
        data: Dict[str, Any],
    ) -> bool:
        """UPDATE a row by primary key. Returns True when a row was matched."""
        if hasattr(self.model, "updated_at"):
            data = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)
            .values(**data)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete(self, entity_id: Union[str, int]) -> bool:
        """Mark a row as deleted without removing it from the database.

        Sets ``is_active = False`` and ``updated_at`` to now.
        There is no ``deleted_at`` or ``is_deleted`` column — do not set them.
        """
        payload: Dict[str, Any] = {
            "is_active": False,
        }
        return await self.update(entity_id, payload)

    async def restore(self, entity_id: Union[str, int]) -> bool:
        """Undo a soft-delete.

        Sets ``is_active = True`` and ``updated_at`` to now.
        There is no ``restored_at`` or ``is_deleted`` column — do not set them.
        """
        payload: Dict[str, Any] = {
            "is_active": True,
        }
        return await self.update(entity_id, payload)

    async def delete(self, entity_id: Union[str, int]) -> bool:
        """Hard-DELETE a row by primary key."""
        stmt = (
            delete(self.model)
            .where(self.model.id == entity_id)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[dict]:
        """INSERT multiple rows in a single round-trip.

        After ``flush()`` SQLAlchemy populates server-generated values (PKs,
        defaults) on each instance via the RETURNING clause used internally by
        asyncpg — no per-row ``refresh()`` call is needed.
        """
        instances = [self.model(**item) for item in items]
        self.db.add_all(instances)
        await self.db.flush()
        return [row_to_dict(inst) for inst in instances]

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        entity_id: Union[str, int],
        include_deleted: bool = False,
    ) -> Optional[dict]:
        """SELECT a single row by primary key.

        When *include_deleted* is False (default) and the model has
        ``is_active``, only an active row is returned.
        """
        clauses = [self.model.id == entity_id]
        if not include_deleted and hasattr(self.model, "is_active"):
            clauses.append(self.model.is_active == True)  # noqa: E712

        stmt = select(self.model).where(and_(*clauses))
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_field(
        self,
        field: str,
        value: Any,
        include_deleted: bool = False,
    ) -> Optional[dict]:
        """SELECT the first row where *field* == *value*.

        Raises
        ------
        ValueError
            If *field* is not a mapped column on the model.
        """
        col = getattr(self.model, field, None)
        if col is None:
            raise ValueError(
                f"'{field}' is not a valid column on {self.model.__name__}"
            )
        clauses = [col == value]
        if not include_deleted and hasattr(self.model, "is_active"):
            clauses.append(self.model.is_active == True)  # noqa: E712

        stmt = select(self.model).where(and_(*clauses)).limit(1)
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_email(
        self,
        email: str,
        include_deleted: bool = False,
    ) -> Optional[dict]:
        """Convenience wrapper: look up a row by its *email* column."""
        return await self.get_by_field("email", email.lower(), include_deleted)

    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[dict]:
        """SELECT all rows matching *filters*, ordered and optionally limited."""
        clauses = self._build_where_clauses(filters, include_deleted)
        stmt = select(self.model)
        if clauses:
            stmt = stmt.where(and_(*clauses))

        order_expr = self._order_column(order_by, order_direction)
        if order_expr is not None:
            stmt = stmt.order_by(order_expr)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[dict], int, int]:
        """
        Two-query paginated SELECT.

        Both the COUNT and the data query run in the same session transaction,
        which guarantees a consistent snapshot without requiring an explicit
        REPEATABLE READ isolation level.

        Returns
        -------
        (items, total_count, total_pages)
        """
        clauses = self._build_where_clauses(filters, include_deleted)
        where_expr = and_(*clauses) if clauses else None

        # --- COUNT query ---
        count_stmt = select(func.count()).select_from(self.model)
        if where_expr is not None:
            count_stmt = count_stmt.where(where_expr)
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)

        # --- DATA query ---
        data_stmt = select(self.model)
        if where_expr is not None:
            data_stmt = data_stmt.where(where_expr)

        order_expr = self._order_column(order_by, order_direction)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)

        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total_count, total_pages

    # ------------------------------------------------------------------
    # Aggregate / existence checks
    # ------------------------------------------------------------------

    async def exists(
        self,
        field: str,
        value: Any,
        include_deleted: bool = False,
    ) -> bool:
        """Return True when at least one row matches *field* == *value*.

        Uses ``SELECT 1 ... LIMIT 1`` rather than ``COUNT(*)`` so the database
        can short-circuit on the first matching row.
        """
        col = getattr(self.model, field, None)
        if col is None:
            raise ValueError(
                f"'{field}' is not a valid column on {self.model.__name__}"
            )
        clauses = [col == value]
        if not include_deleted and hasattr(self.model, "is_active"):
            clauses.append(self.model.is_active == True)  # noqa: E712

        stmt = (
            select(literal(1))
            .select_from(self.model)
            .where(and_(*clauses))
            .limit(1)
        )
        result = (await self.db.execute(stmt)).scalar()
        return result is not None

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """Return the number of rows matching *filters*."""
        clauses = self._build_where_clauses(filters, include_deleted)
        stmt = select(func.count()).select_from(self.model)
        if clauses:
            stmt = stmt.where(and_(*clauses))
        return (await self.db.execute(stmt)).scalar_one()
