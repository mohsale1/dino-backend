"""
PersonaService — business logic for personas (outlet/branch profiles).
workspace_id removed from personas table — linked via workspace_personas.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError, NotFoundError
from src.core.Storage import upload_persona_logo
from src.models.Workspace import workspace_personas
from src.repositories.PersonaRepository import PersonaRepository

logger = logging.getLogger(__name__)


class PersonaService(BaseService):
    """Service for managing personas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.persona_repo = PersonaRepository(db)
        super().__init__(self.persona_repo)

    async def create_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a persona and link it to the workspace via workspace_personas.

        Raises
        ------
        BadRequestError
            If workspace_id is missing.
        ConflictError
            If a persona with the same name already exists in this workspace.
        """
        workspace_id = data.pop("workspace_id", None)
        if not workspace_id:
            raise BadRequestError("workspace_id is required to create a persona")

        if await self.persona_repo.name_exists_for_workspace(data["name"], workspace_id):
            logger.warning(
                "persona.create.duplicate_name workspace_id=%s name=%r",
                workspace_id, data["name"],
            )
            raise ConflictError(
                f"A persona named '{data['name']}' already exists in this workspace"
            )

        data.setdefault("is_active", True)

        async with self.db.begin_nested():
            created = await self.persona_repo.create(data)
            persona_id = created["id"]
            await self.db.execute(
                pg_insert(workspace_personas)
                .values(workspace_id=workspace_id, persona_id=persona_id)
                .on_conflict_do_nothing()
            )

        logger.info(
            "persona.created persona_id=%s workspace_id=%s name=%r",
            persona_id, workspace_id, created.get("name"),
        )
        return created

    async def get_paginated_personas(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated personas linked to a workspace."""
        logger.debug(
            "persona.list workspace_id=%s page=%s page_size=%s include_deleted=%s",
            workspace_id, page, page_size, include_deleted,
        )
        result = await self.persona_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        logger.debug(
            "persona.list.result workspace_id=%s total=%s returned=%s",
            workspace_id, result[1], len(result[0]),
        )
        return result

    async def get_persona_by_id(
        self,
        persona_id: int,
        workspace_id: int,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a persona by ID. workspace_id reserved for future scoping."""
        return await self.persona_repo.get_by_id(persona_id, include_deleted=include_deleted)


    async def update_persona(
        self,
        persona_id: int,
        workspace_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        Update a persona scoped to workspace. Single round-trip.

        Raises
        ------
        ConflictError
            If the new name conflicts with another persona in the same workspace.
        """
        if "name" in data:
            if await self.persona_repo.name_exists_for_workspace(
                data["name"], workspace_id, exclude_id=persona_id
            ):
                logger.warning(
                    "persona.update.duplicate_name persona_id=%s workspace_id=%s name=%r",
                    persona_id, workspace_id, data["name"],
                )
                raise ConflictError(
                    f"A persona named '{data['name']}' already exists in this workspace"
                )

        updated = await self.persona_repo.update_for_workspace(persona_id, workspace_id, data)
        if updated:
            logger.info(
                "persona.updated persona_id=%s workspace_id=%s fields=%s",
                persona_id, workspace_id, list(data.keys()),
            )
        return updated

    async def toggle_open(
        self,
        persona_id: int,
        workspace_id: int,
        is_open: bool,
    ) -> bool:
        """Toggle the is_open status of a persona."""
        updated = await self.persona_repo.update_for_workspace(
            persona_id, workspace_id, {"is_open": is_open}
        )
        if updated:
            logger.info(
                "persona.toggle_open persona_id=%s workspace_id=%s is_open=%s",
                persona_id, workspace_id, is_open,
            )
        return updated

    async def deactivate_persona(
        self,
        persona_id: int,
        workspace_id: int,
        deactivate: bool,
    ) -> bool:
        """
        Toggle the is_deactivated flag on a persona (billing-level suspension).
        is_deactivated=True  → persona is suspended (billing issue, admin action)
        is_deactivated=False → persona is reinstated

        This is separate from soft-delete (is_active). A deactivated persona
        still exists and can be reactivated; a deleted persona is hidden.
        """
        updated = await self.persona_repo.update_for_workspace(
            persona_id, workspace_id, {"is_deactivated": deactivate}
        )
        if updated:
            action = "deactivated" if deactivate else "reactivated"
            logger.info(
                "persona.%s persona_id=%s workspace_id=%s",
                action, persona_id, workspace_id,
            )
        return updated

    async def soft_delete_persona(self, persona_id: int) -> bool:
        """Soft-delete a persona."""
        deleted = await self.persona_repo.soft_delete(persona_id)
        if deleted:
            logger.info("persona.deleted persona_id=%s", persona_id)
        return deleted

    async def restore_persona(self, persona_id: int) -> bool:
        """Restore a soft-deleted persona."""
        restored = await self.persona_repo.restore(persona_id)
        if restored:
            logger.info("persona.restored persona_id=%s", persona_id)
        return restored

    async def upload_logo(
        self,
        persona_id: int,
        workspace_id: int,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """
        Upload persona logo to GCS and persist the URL.

        Raises
        ------
        NotFoundError
            If the persona does not exist or does not belong to this workspace.
        """
        persona = await self.get_persona_by_id(persona_id, workspace_id)
        if not persona:
            logger.warning(
                "persona.upload_logo.not_found persona_id=%s workspace_id=%s",
                persona_id, workspace_id,
            )
            raise NotFoundError("Persona not found")

        logger.info(
            "persona.upload_logo.start persona_id=%s workspace_id=%s",
            persona_id, workspace_id,
        )

        url = await upload_persona_logo(
            workspace_id=workspace_id,
            persona_id=persona_id,
            file_data=file_data,
            content_type=content_type,
        )

        await self.persona_repo.update_for_workspace(
            persona_id, workspace_id, {"logo_url": url}
        )

        logger.info(
            "persona.upload_logo.success persona_id=%s workspace_id=%s url=%s",
            persona_id, workspace_id, url,
        )
        return url
