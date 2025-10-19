"""
Rating Service
Handles rating calculations and updates for venues and menu items
"""

from typing import Dict, Any, Optional, Literal
from app.database.firestore import venue_repo, menu_item_repo
from app.core.logging_config import get_logger

logger = get_logger(__name__)

EntityType = Literal["venue", "menu_item"]


class RatingService:
    """Service for managing venue and menu item ratings"""
    
    @staticmethod
    def _get_repository(entity_type: EntityType):
        """Get the appropriate repository for the entity type"""
        if entity_type == "venue":
            return venue_repo
        elif entity_type == "menu_item":
            return menu_item_repo
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")
    
    @staticmethod
    async def add_rating(entity_id: str, rating: float, entity_type: EntityType = "venue") -> Dict[str, Any]:
        """
        Add a new rating to a venue or menu item
        
        Args:
            entity_id: The entity ID (venue or menu item)
            rating: Rating value (1-5)
            entity_type: Type of entity ("venue" or "menu_item")
            
        Returns:
            Updated entity data with new rating statistics
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        try:
            repo = RatingService._get_repository(entity_type)
            
            # Get current entity data
            entity = await repo.get_by_id(entity_id)
            if not entity:
                raise ValueError(f"{entity_type.title()} {entity_id} not found")
            
            # Get current rating data
            current_rating_total = entity.get('rating_total', 0.0)
            current_rating_count = entity.get('rating_count', 0)
            
            # Calculate new totals
            new_rating_total = current_rating_total + rating
            new_rating_count = current_rating_count + 1
            new_average_rating = new_rating_total / new_rating_count
            
            # Update entity
            update_data = {
                'rating_total': new_rating_total,
                'rating_count': new_rating_count
            }
            
            updated_entity = await repo.update(entity_id, update_data)
            
            logger.info(f"Added rating {rating} to {entity_type} {entity_id}. New average: {new_average_rating:.2f}")
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'rating_total': new_rating_total,
                'rating_count': new_rating_count,
                'average_rating': round(new_average_rating, 2),
                'added_rating': rating
            }
            
        except Exception as e:
            logger.error(f"Error adding rating to {entity_type} {entity_id}: {e}")
            raise
    
    @staticmethod
    async def update_rating(entity_id: str, old_rating: float, new_rating: float, entity_type: EntityType = "venue") -> Dict[str, Any]:
        """
        Update an existing rating for a venue or menu item
        
        Args:
            entity_id: The entity ID (venue or menu item)
            old_rating: Previous rating value
            new_rating: New rating value (1-5)
            entity_type: Type of entity ("venue" or "menu_item")
            
        Returns:
            Updated entity data with new rating statistics
        """
        if not 1 <= new_rating <= 5:
            raise ValueError("New rating must be between 1 and 5")
        
        if not 1 <= old_rating <= 5:
            raise ValueError("Old rating must be between 1 and 5")
        
        try:
            repo = RatingService._get_repository(entity_type)
            
            # Get current entity data
            entity = await repo.get_by_id(entity_id)
            if not entity:
                raise ValueError(f"{entity_type.title()} {entity_id} not found")
            
            # Get current rating data
            current_rating_total = entity.get('rating_total', 0.0)
            current_rating_count = entity.get('rating_count', 0)
            
            if current_rating_count == 0:
                raise ValueError(f"Cannot update rating for {entity_type} with no existing ratings")
            
            # Calculate new totals (subtract old, add new)
            new_rating_total = current_rating_total - old_rating + new_rating
            new_average_rating = new_rating_total / current_rating_count
            
            # Update entity
            update_data = {
                'rating_total': new_rating_total
            }
            
            updated_entity = await repo.update(entity_id, update_data)
            
            logger.info(f"Updated rating for {entity_type} {entity_id} from {old_rating} to {new_rating}. New average: {new_average_rating:.2f}")
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'rating_total': new_rating_total,
                'rating_count': current_rating_count,
                'average_rating': round(new_average_rating, 2),
                'old_rating': old_rating,
                'new_rating': new_rating
            }
            
        except Exception as e:
            logger.error(f"Error updating rating for {entity_type} {entity_id}: {e}")
            raise
    
    @staticmethod
    async def remove_rating(entity_id: str, rating: float, entity_type: EntityType = "venue") -> Dict[str, Any]:
        """
        Remove a rating from a venue or menu item
        
        Args:
            entity_id: The entity ID (venue or menu item)
            rating: Rating value to remove (1-5)
            entity_type: Type of entity ("venue" or "menu_item")
            
        Returns:
            Updated entity data with new rating statistics
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        try:
            repo = RatingService._get_repository(entity_type)
            
            # Get current entity data
            entity = await repo.get_by_id(entity_id)
            if not entity:
                raise ValueError(f"{entity_type.title()} {entity_id} not found")
            
            # Get current rating data
            current_rating_total = entity.get('rating_total', 0.0)
            current_rating_count = entity.get('rating_count', 0)
            
            if current_rating_count == 0:
                raise ValueError(f"Cannot remove rating from {entity_type} with no existing ratings")
            
            if current_rating_total < rating:
                raise ValueError("Cannot remove rating: would result in negative total")
            
            # Calculate new totals
            new_rating_total = current_rating_total - rating
            new_rating_count = current_rating_count - 1
            new_average_rating = new_rating_total / new_rating_count if new_rating_count > 0 else 0.0
            
            # Update entity
            update_data = {
                'rating_total': new_rating_total,
                'rating_count': new_rating_count
            }
            
            updated_entity = await repo.update(entity_id, update_data)
            
            logger.info(f"Removed rating {rating} from {entity_type} {entity_id}. New average: {new_average_rating:.2f}")
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'rating_total': new_rating_total,
                'rating_count': new_rating_count,
                'average_rating': round(new_average_rating, 2),
                'removed_rating': rating
            }
            
        except Exception as e:
            logger.error(f"Error removing rating from {entity_type} {entity_id}: {e}")
            raise
    
    @staticmethod
    async def get_rating_stats(entity_id: str, entity_type: EntityType = "venue") -> Dict[str, Any]:
        """
        Get rating statistics for a venue or menu item
        
        Args:
            entity_id: The entity ID (venue or menu item)
            entity_type: Type of entity ("venue" or "menu_item")
            
        Returns:
            Rating statistics
        """
        try:
            repo = RatingService._get_repository(entity_type)
            
            entity = await repo.get_by_id(entity_id)
            if not entity:
                raise ValueError(f"{entity_type.title()} {entity_id} not found")
            
            rating_total = entity.get('rating_total', 0.0)
            rating_count = entity.get('rating_count', 0)
            average_rating = rating_total / rating_count if rating_count > 0 else 0.0
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'entity_name': entity.get('name', 'Unknown'),
                'rating_total': rating_total,
                'rating_count': rating_count,
                'average_rating': round(average_rating, 2),
                'has_ratings': rating_count > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting rating stats for {entity_type} {entity_id}: {e}")
            raise
    
    @staticmethod
    def calculate_average_rating(rating_total: float, rating_count: int) -> float:
        """
        Calculate average rating from total and count
        
        Args:
            rating_total: Sum of all ratings
            rating_count: Number of ratings
            
        Returns:
            Average rating rounded to 2 decimal places
        """
        if rating_count == 0:
            return 0.0
        return round(rating_total / rating_count, 2)
    
    # Convenience methods for venues (backward compatibility)
    @staticmethod
    async def add_venue_rating(venue_id: str, rating: float) -> Dict[str, Any]:
        """Add rating to a venue"""
        return await RatingService.add_rating(venue_id, rating, "venue")
    
    @staticmethod
    async def update_venue_rating(venue_id: str, old_rating: float, new_rating: float) -> Dict[str, Any]:
        """Update venue rating"""
        return await RatingService.update_rating(venue_id, old_rating, new_rating, "venue")
    
    @staticmethod
    async def remove_venue_rating(venue_id: str, rating: float) -> Dict[str, Any]:
        """Remove venue rating"""
        return await RatingService.remove_rating(venue_id, rating, "venue")
    
    @staticmethod
    async def get_venue_rating_stats(venue_id: str) -> Dict[str, Any]:
        """Get venue rating statistics"""
        return await RatingService.get_rating_stats(venue_id, "venue")
    
    # Convenience methods for menu items
    @staticmethod
    async def add_menu_item_rating(menu_item_id: str, rating: float) -> Dict[str, Any]:
        """Add rating to a menu item"""
        return await RatingService.add_rating(menu_item_id, rating, "menu_item")
    
    @staticmethod
    async def update_menu_item_rating(menu_item_id: str, old_rating: float, new_rating: float) -> Dict[str, Any]:
        """Update menu item rating"""
        return await RatingService.update_rating(menu_item_id, old_rating, new_rating, "menu_item")
    
    @staticmethod
    async def remove_menu_item_rating(menu_item_id: str, rating: float) -> Dict[str, Any]:
        """Remove menu item rating"""
        return await RatingService.remove_rating(menu_item_id, rating, "menu_item")
    
    @staticmethod
    async def get_menu_item_rating_stats(menu_item_id: str) -> Dict[str, Any]:
        """Get menu item rating statistics"""
        return await RatingService.get_rating_stats(menu_item_id, "menu_item")


# Singleton instance
rating_service = RatingService()