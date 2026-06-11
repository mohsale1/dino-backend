"""
ItemService — business logic for menu items.
Scoped by persona_id. Category must belong to the same persona.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError, NotFoundError
from src.core.Storage import upload_item_image
from src.repositories.ItemRepository import ItemRepository

logger = logging.getLogger(__name__)


class ItemService(BaseService):
    """Service for managing menu items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.item_repo = ItemRepository(db)
        super().__init__(self.item_repo)

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new menu item scoped to persona.

        Raises
        ------
        BadRequestError
            If persona_id or category_id is missing.
        NotFoundError
            If the category does not belong to this persona.
        ConflictError
            If an active item with the same name exists in the same category.
        """
        persona_id = data.get("persona_id")
        category_id = data.get("category_id")

        if not persona_id:
            raise BadRequestError("persona_id is required to create an item")
        if not category_id:
            raise BadRequestError("category_id is required to create an item")

        logger.debug(
            "item.create.validating persona_id=%s category_id=%s name=%r",
            persona_id, category_id, data.get("name"),
        )

        if not await self.item_repo.category_belongs_to_persona(category_id, persona_id):
            logger.warning(
                "item.create.invalid_category persona_id=%s category_id=%s",
                persona_id, category_id,
            )
            raise NotFoundError("Category not found or does not belong to this persona")

        if await self.item_repo.name_exists_for_persona(data["name"], persona_id, category_id):
            logger.warning(
                "item.create.duplicate_name persona_id=%s category_id=%s name=%r",
                persona_id, category_id, data["name"],
            )
            raise ConflictError(
                f"An item named '{data['name']}' already exists in this category"
            )

        data.setdefault("is_active", True)
        data.setdefault("is_available", True)

        item = await self.item_repo.create_item(data)
        logger.info(
            "item.created item_id=%s persona_id=%s category_id=%s name=%r",
            item.get("id"), persona_id, category_id, item.get("name"),
        )
        return item

    async def get_paginated_items(
        self,
        persona_id: int,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active items scoped to persona."""
        logger.debug(
            "item.list persona_id=%s category_id=%s is_available=%s is_vegetarian=%s "
            "search=%r page=%s page_size=%s",
            persona_id, category_id, is_available, is_vegetarian, search, page, page_size,
        )
        result = await self.item_repo.get_paginated_by_persona(
            persona_id=persona_id,
            page=page,
            page_size=page_size,
            category_id=category_id,
            is_available=is_available,
            is_vegetarian=is_vegetarian,
            search_query=search,
        )
        logger.debug(
            "item.list.result persona_id=%s total=%s returned=%s",
            persona_id, result[1], len(result[0]),
        )
        return result

    async def get_item_for_persona(
        self,
        item_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single active item scoped to persona."""
        logger.debug("item.get item_id=%s persona_id=%s", item_id, persona_id)
        item = await self.item_repo.get_by_id_for_persona(item_id, persona_id)
        if item:
            logger.debug("item.get.found item_id=%s name=%r", item_id, item.get("name"))
        else:
            logger.debug("item.get.not_found item_id=%s persona_id=%s", item_id, persona_id)
        return item

    async def update_item(
        self,
        item_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an item scoped to persona.

        Raises
        ------
        NotFoundError
            If a new category_id does not belong to this persona.
        ConflictError
            If the new name conflicts with another item in the same category.
        """
        # Validate new category belongs to persona
        if "category_id" in data:
            if not await self.item_repo.category_belongs_to_persona(
                data["category_id"], persona_id
            ):
                logger.warning(
                    "item.update.invalid_category item_id=%s persona_id=%s category_id=%s",
                    item_id, persona_id, data["category_id"],
                )
                raise NotFoundError("Category not found or does not belong to this persona")

        # Duplicate name check — need category_id for scope
        if "name" in data:
            # Fetch current item to get category_id if not being changed
            current = await self.item_repo.get_by_id_for_persona(item_id, persona_id)
            if not current:
                logger.warning(
                    "item.update.not_found item_id=%s persona_id=%s",
                    item_id, persona_id,
                )
                raise NotFoundError("Item not found")

            check_category_id = data.get("category_id", current["category_id"])
            if await self.item_repo.name_exists_for_persona(
                data["name"], persona_id, check_category_id, exclude_id=item_id
            ):
                logger.warning(
                    "item.update.duplicate_name item_id=%s persona_id=%s name=%r",
                    item_id, persona_id, data["name"],
                )
                raise ConflictError(
                    f"An item named '{data['name']}' already exists in this category"
                )

        updated = await self.item_repo.update_for_persona(item_id, persona_id, data)
        if updated:
            logger.info(
                "item.updated item_id=%s persona_id=%s fields=%s",
                item_id, persona_id, list(data.keys()),
            )
        return updated

    async def update_availability(
        self,
        item_id: int,
        persona_id: int,
        is_available: bool,
    ) -> bool:
        """Toggle the availability of an item scoped to persona."""
        updated = await self.item_repo.update_for_persona(
            item_id, persona_id, {"is_available": is_available}
        )
        if updated:
            logger.info(
                "item.availability.updated item_id=%s persona_id=%s is_available=%s",
                item_id, persona_id, is_available,
            )
        return updated

    async def soft_delete_item(
        self,
        item_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an item scoped to persona."""
        deleted = await self.item_repo.soft_delete_for_persona(item_id, persona_id)
        if deleted:
            logger.info("item.deleted item_id=%s persona_id=%s", item_id, persona_id)
        return deleted

    async def restore_item(
        self,
        item_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted item scoped to persona."""
        restored = await self.item_repo.restore_for_persona(item_id, persona_id)
        if restored:
            logger.info("item.restored item_id=%s persona_id=%s", item_id, persona_id)
        return restored

    async def upload_image(
        self,
        item_id: int,
        persona_id: int,
        workspace_id: int,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """
        Upload item image to GCS and persist the URL on the item row.

        Raises
        ------
        NotFoundError
            If the item does not exist or does not belong to this persona.
        BadRequestError / InternalError
            Propagated from the GCS upload layer.
        """
        item = await self.item_repo.get_by_id_for_persona(item_id, persona_id)
        if not item:
            logger.warning(
                "item.upload_image.not_found item_id=%s persona_id=%s",
                item_id, persona_id,
            )
            raise NotFoundError("Item not found")

        logger.info(
            "item.upload_image.start item_id=%s persona_id=%s workspace_id=%s",
            item_id, persona_id, workspace_id,
        )

        url = await upload_item_image(
            workspace_id=workspace_id,
            persona_id=persona_id,
            item_id=item_id,
            file_data=file_data,
            content_type=content_type,
        )

        await self.item_repo.update_for_persona(item_id, persona_id, {"image_url": url})

        logger.info(
            "item.upload_image.success item_id=%s persona_id=%s url=%s",
            item_id, persona_id, url,
        )
        return url
