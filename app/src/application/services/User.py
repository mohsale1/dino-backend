"""
ApplicationUserService — manages application users (user_type=1).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.core.Security import get_password_hash
from src.models.Role import Role
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class ApplicationUserService:
    """Service for managing application users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application user and optionally link to personas."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from src.models.User import user_personas

        # Extract persona_ids — not a column on User, handled separately via user_personas
        persona_ids: Optional[List[int]] = user_data.pop("persona_ids", None)

        if "password" in user_data:
            user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        user_data["user_type"] = 1
        user_data.setdefault("is_active", True)

        result = await self.user_repo.create(user_data)
        user_id = result["id"]

        # Link user to personas via the user_personas association table
        if persona_ids:
            for pid in persona_ids:
                stmt = (
                    pg_insert(user_personas)
                    .values(user_id=user_id, persona_id=pid)
                    .on_conflict_do_nothing()
                )
                await self.db.execute(stmt)

        result.pop("password_hash", None)
        result["persona_ids"] = persona_ids or []
        return result


    async def get_by_id(
        self, user_id: int, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        return await self.user_repo.get_by_id(user_id, include_deleted)

    async def get_user_with_role(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with role resolved, password_hash stripped."""
        user = await self.get_by_id(user_id, include_deleted=False)
        if not user:
            return None
        users = await self._enrich_and_sanitize([user])
        return users[0] if users else None

    async def get_paginated_users(
        self,
        workspace_id: Optional[int] = None,
        persona_id: Optional[int] = None,
        role_id: Optional[int] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated users with role enrichment."""
        items, total, total_pages = await self.user_repo.get_paginated_users(
            workspace_id=workspace_id,
            persona_id=persona_id,
            role_id=role_id,
            search_query=search_query,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        return await self._enrich_and_sanitize(items), total, total_pages

    async def _enrich_and_sanitize(
        self, users: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve role_id -> role object and strip sensitive fields."""
        sanitized: List[Dict[str, Any]] = []
        role_ids: set = set()
        for user in users:
            user = {k: v for k, v in user.items() if k != "password_hash"}
            sanitized.append(user)
            role_id = user.get("role_id")
            if role_id is not None and role_id not in role_ids:
                role_ids.add(role_id)

        role_cache: Dict[int, Dict[str, Any]] = {}
        if role_ids:
            stmt = select(Role).where(Role.id.in_(role_ids))
            result = await self.db.execute(stmt)
            for row in result.scalars().all():
                d = row_to_dict(row)
                role_cache[d["id"]] = d

        result_list = []
        for user in sanitized:
            role_id = user.get("role_id")
            if role_id is not None:
                role = role_cache.get(role_id)
                if role:
                    user["role"] = {
                        "id": role.get("id"),
                        "name": role.get("name"),
                        "role_type": role.get("role_type", 1),
                    }
            result_list.append(user)

        return result_list


    async def update_user(
        self,
        user_id: int,
        data: Dict[str, Any],
        workspace_id: Optional[int] = None,
    ) -> bool:
        """Update user, hashing password if present. Optionally scope to workspace."""
        if workspace_id is not None:
            existing = await self.user_repo.get_by_id(user_id)
            if not existing or existing.get("workspace_id") != workspace_id:
                return False
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        return await self.user_repo.update(user_id, data)


    async def soft_delete_user(self, user_id: int) -> bool:
        return await self.user_repo.soft_delete(user_id)

    async def restore_user(self, user_id: int) -> bool:
        return await self.user_repo.restore(user_id)

    async def email_exists(
        self, email: str, workspace_id: int, exclude_id: Optional[int] = None
    ) -> bool:
        return await self.user_repo.email_exists(email, workspace_id, exclude_id)

    async def validate_application_role(self, role_id: int) -> bool:
        """Return True if the role exists and is an application role (role_type=1)."""
        role = await self.role_repo.get_by_id(role_id)
        return role.get("role_type") == 1 if role else False

    async def get_users_by_role(
        self, role_id: int, workspace_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {"role_id": role_id}
        if workspace_id:
            filters["workspace_id"] = workspace_id
        items = await self.user_repo.get_all(filters=filters)
        return await self._enrich_and_sanitize(items)

    async def get_users_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        items = await self.user_repo.get_by_workspace(workspace_id)
        return await self._enrich_and_sanitize(items)

next

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
            clauses.append(self.model.is_active.is_(True))

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
        if order_direction.lower() not in ("asc", "desc"):
            logger.warning(
                "BaseRepository._order_column: invalid order_direction '%s' — "
                "defaulting to 'asc'.",
                order_direction,
            )
            order_direction = "asc"
        return col.desc() if order_direction.lower() == "desc" else col.asc()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: Dict[str, Any]) -> dict:
        """INSERT a new row, flush to obtain server-generated values, and return as a dict.

        flush() sends the INSERT within the current transaction without committing.
        The caller's session (get_db) is responsible for the final commit.
        """
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
        return await self.update(entity_id, {"is_active": False})

    async def restore(self, entity_id: Union[str, int]) -> bool:
        """Undo a soft-delete.

        Sets ``is_active = True`` and ``updated_at`` to now.
        There is no ``restored_at`` or ``is_deleted`` column — do not set them.
        """
        return await self.update(entity_id, {"is_active": True})

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

        After ``flush()``, each instance is explicitly refreshed so that
        server-generated values (PKs, defaults, server_default columns) are
        fully populated before the dicts are returned.
        """
        if len(items) > 500:
            raise ValueError(f"bulk_create limit is 500 rows, got {len(items)}")
        instances = [self.model(**item) for item in items]
        self.db.add_all(instances)
        await self.db.flush()
        for inst in instances:
            await self.db.refresh(inst)
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
            clauses.append(self.model.is_active.is_(True))

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
            clauses.append(self.model.is_active.is_(True))

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

        Returns
        -------
        (items, total_count, total_pages)
        """
        page_size = min(page_size, 200)
        clauses = self._build_where_clauses(filters, include_deleted)
        where_expr = and_(*clauses) if clauses else None

        count_stmt = select(func.count()).select_from(self.model)
        if where_expr is not None:
            count_stmt = count_stmt.where(where_expr)
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)

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
            clauses.append(self.model.is_active.is_(True))

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
