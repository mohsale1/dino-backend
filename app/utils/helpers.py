"""
Helper Utility Functions
Essential utilities for menu items and data processing
"""

from typing import Dict, Any, List
from datetime import datetime
from app.models.enums import SpiceLevel

# =============================================================================
# MENU ITEM UTILITIES
# =============================================================================

def ensure_menu_item_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all required fields are present in menu item data with proper defaults.

    Args:
        item (Dict[str, Any]): Menu item dictionary

    Returns:
        Dict[str, Any]: Menu item with all required fields and safe defaults
    """
    try:
        # Make a copy to avoid mutating the original
        item = item.copy()

        # Calculate average rating safely
        rating_count = max(0, int(item.get("rating_count", 0)))
        rating_total = max(0.0, float(item.get("rating_total", 0.0)))
        item["average_rating"] = round(rating_total / rating_count, 2) if rating_count > 0 else 0.0

        # Default values for required fields
        defaults = {
            "rating_total": 0.0,
            "rating_count": 0,
            "image_urls": [],
            "is_available": True,
            "is_vegetarian": True,
            "spice_level": SpiceLevel.MILD.value,
            "preparation_time_minutes": 15,
            "base_price": 0.0,
            "name": "Unknown Item",
            "description": "",
            "venue_id": "",
            "category_id": "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Apply defaults for missing fields
        for field, default_value in defaults.items():
            if field not in item or item[field] is None:
                item[field] = default_value

        # Ensure required string fields are not empty
        if not str(item.get("name", "")).strip():
            item["name"] = "Unknown Item"
        item["description"] = item.get("description", "") or ""
        item["venue_id"] = item.get("venue_id", "") or ""
        item["category_id"] = item.get("category_id", "") or ""

        # Ensure numeric fields
        try:
            item["base_price"] = max(0.0, float(item.get("base_price", 0.0)))
        except (ValueError, TypeError):
            item["base_price"] = 0.0

        try:
            item["preparation_time_minutes"] = max(1, int(item.get("preparation_time_minutes", 15)))
        except (ValueError, TypeError):
            item["preparation_time_minutes"] = 15

        # Ensure boolean fields
        item["is_available"] = bool(item.get("is_available", True))
        item["is_vegetarian"] = bool(item.get("is_vegetarian", True))

        # Ensure list fields
        if not isinstance(item.get("image_urls"), list):
            item["image_urls"] = []

        # Ensure datetime fields are proper datetime objects
        for date_field in ["created_at", "updated_at"]:
            value = item.get(date_field)
            if isinstance(value, str):
                try:
                    # Handle ISO format with Z suffix
                    if value.endswith("Z"):
                        value = value[:-1] + "+00:00"
                    item[date_field] = datetime.fromisoformat(value)
                except Exception:
                    item[date_field] = datetime.utcnow()
            elif not isinstance(value, datetime):
                item[date_field] = datetime.utcnow()

        # Ensure spice_level is valid
        valid_spice_levels = [level.value for level in SpiceLevel]
        if item.get("spice_level") not in valid_spice_levels:
            item["spice_level"] = SpiceLevel.MILD.value

        return item

    except Exception:
        # Fallback minimal valid item if processing fails
        return {
            "id": item.get("id", ""),
            "venue_id": item.get("venue_id", ""),
            "category_id": item.get("category_id", ""),
            "name": item.get("name", "Unknown Item"),
            "description": item.get("description", ""),
            "base_price": 0.0,
            "is_vegetarian": True,
            "spice_level": SpiceLevel.MILD.value,
            "preparation_time_minutes": 15,
            "image_urls": [],
            "is_available": True,
            "rating_total": 0.0,
            "rating_count": 0,
            "average_rating": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }


def process_menu_items_for_response(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a list of menu items to ensure they have all required fields.

    Args:
        items (List[Dict[str, Any]]): List of menu item dictionaries

    Returns:
        List[Dict[str, Any]]: List of processed menu items
    """
    return [ensure_menu_item_fields(item) for item in items]