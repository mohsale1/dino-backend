"""
TableService — business logic for restaurant tables.
Scoped by persona_id only.
"""

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError, NotFoundError
from src.repositories.TableRepository import TableRepository

logger = logging.getLogger(__name__)


class TableService(BaseService):
    """Service for managing restaurant tables."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.table_repo = TableRepository(db)
        super().__init__(self.table_repo)

    async def create_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new table scoped to persona.

        Raises
        ------
        BadRequestError
            If persona_id or area_id is missing.
        ConflictError
            If a table with the same number already exists for this persona.
        """
        persona_id = data.get("persona_id")
        if not persona_id:
            raise BadRequestError("persona_id is required to create a table")
        if not data.get("area_id"):
            raise BadRequestError("area_id is required to create a table")

        if await self.table_repo.table_number_exists_for_persona(
            data["table_number"], persona_id
        ):
            logger.warning(
                "table.create.duplicate persona_id=%s table_number=%r",
                persona_id, data["table_number"],
            )
            raise ConflictError(
                f"Table '{data['table_number']}' already exists for this persona"
            )

        data.setdefault("is_active", True)
        data.setdefault("status", "available")
        table = await self.table_repo.create_table(data)
        logger.info(
            "table.created table_id=%s persona_id=%s table_number=%r",
            table.get("id"), persona_id, table.get("table_number"),
        )
        return table

    async def get_paginated_tables(
        self,
        persona_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated tables scoped to persona."""
        logger.debug(
            "table.list persona_id=%s area_id=%s status=%s page=%s page_size=%s",
            persona_id, area_id, status, page, page_size,
        )
        return await self.table_repo.get_paginated_by_persona(
            persona_id=persona_id,
            area_id=area_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def get_table_for_persona(
        self,
        table_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active table scoped to persona."""
        return await self.table_repo.get_by_id_for_persona(table_id, persona_id)

    async def update_table(
        self,
        table_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update a table scoped to persona.

        Raises
        ------
        ConflictError
            If the new table_number conflicts with another table in the same persona.
        """
        if "table_number" in data:
            if await self.table_repo.table_number_exists_for_persona(
                data["table_number"], persona_id, exclude_id=table_id
            ):
                logger.warning(
                    "table.update.duplicate table_id=%s persona_id=%s table_number=%r",
                    table_id, persona_id, data["table_number"],
                )
                raise ConflictError(
                    f"Table '{data['table_number']}' already exists for this persona"
                )

        updated = await self.table_repo.update_for_persona(table_id, persona_id, data)
        if updated:
            logger.info(
                "table.updated table_id=%s persona_id=%s fields=%s",
                table_id, persona_id, list(data.keys()),
            )
        return updated

    async def update_table_status(
        self,
        table_id: int,
        persona_id: int,
        status: str,
    ) -> bool:
        """Update only the status field of a table scoped to persona."""
        updated = await self.table_repo.update_for_persona(
            table_id, persona_id, {"status": status}
        )
        if updated:
            logger.info(
                "table.status.updated table_id=%s persona_id=%s status=%s",
                table_id, persona_id, status,
            )
        return updated

    async def soft_delete_table(self, table_id: int, persona_id: int) -> bool:
        """Soft-delete a table scoped to persona."""
        deleted = await self.table_repo.soft_delete_for_persona(table_id, persona_id)
        if deleted:
            logger.info("table.deleted table_id=%s persona_id=%s", table_id, persona_id)
        return deleted

    async def restore_table(self, table_id: int, persona_id: int) -> bool:
        """Restore a soft-deleted table scoped to persona."""
        restored = await self.table_repo.restore_for_persona(table_id, persona_id)
        if restored:
            logger.info("table.restored table_id=%s persona_id=%s", table_id, persona_id)
        return restored

    async def get_table_status_summary(self, persona_id: int) -> Dict[str, int]:
        """Return counts of tables grouped by status scoped to persona."""
        return await self.table_repo.get_status_counts(persona_id)

    async def generate_qr_code(
        self,
        table_id: int,
        persona_id: int,
        frontend_url: str,
    ) -> bytes:
        """Fetch the table, build a menu URL, generate a QR code PNG and return raw bytes."""
        table = await self.table_repo.get_by_id_for_persona(table_id, persona_id)
        if not table:
            raise NotFoundError("Table not found")

        url = f"{frontend_url.rstrip('/')}/menu/{persona_id}/{table_id}"
        logger.info(
            "table.qr_code.generated table_id=%s persona_id=%s url=%s",
            table_id, persona_id, url,
        )

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
