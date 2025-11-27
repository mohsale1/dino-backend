"""
Venue Service
Business logic for venue management
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.entities import VenueStatus, SubscriptionStatus
from app.database.repository_manager import get_venue_repo, get_menu_item_repo, get_table_repo, get_order_repo, get_customer_repo
from app.core.logging import get_logger

logger = get_logger(__name__)


def clean_venue_status(venue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and normalize venue status field"""
    if 'status' in venue_data:
        status_value = venue_data['status']
        if isinstance(status_value, str):
            cleaned_status = status_value.strip("'\"")
            valid_statuses = [e.value for e in VenueStatus]
            if cleaned_status in valid_statuses:
                venue_data['status'] = cleaned_status
            else:
                venue_data['status'] = VenueStatus.ACTIVE.value
        else:
            venue_data['status'] = VenueStatus.ACTIVE.value
    else:
        venue_data['status'] = VenueStatus.ACTIVE.value
    
    return venue_data


class VenueService:
    """Service for venue business logic"""
    
    def __init__(self):
        self.repo = get_venue_repo()
    
    async def get_venue_analytics(self, venue_id: str) -> Dict[str, Any]:
        """Get basic analytics for a venue"""
        venue_data = await self.repo.get_by_id(venue_id)
        if not venue_data:
            return None
        
        # Get related data counts
        menu_repo = get_menu_item_repo()
        table_repo = get_table_repo()
        order_repo = get_order_repo()
        customer_repo = get_customer_repo()
        
        # Count items
        menu_items = await menu_repo.get_by_venue(venue_id)
        tables = await table_repo.get_by_venue(venue_id)
        orders = await order_repo.get_by_venue(venue_id, limit=100)
        customers = await customer_repo.get_by_venue(venue_id)
        
        return {
            "venue_id": venue_id,
            "total_menu_items": len(menu_items),
            "total_tables": len(tables),
            "recent_orders": len(orders),
            "total_customers": len(customers),
            "rating": venue_data.get('rating', 0.0),
            "total_reviews": venue_data.get('total_reviews', 0),
            "subscription_status": venue_data.get('subscription_status'),
            "is_active": venue_data.get('is_active', False)
        }
    
    async def toggle_venue_status(self, venue_id: str, is_open: bool, reason: Optional[str], user_id: str) -> Dict[str, Any]:
        """Toggle venue open/closed status"""
        update_data = {
            'is_open': is_open,
            'status_updated_at': datetime.utcnow(),
            'status_updated_by': user_id
        }
        
        if reason:
            update_data['status_reason'] = reason
        
        await self.repo.update(venue_id, update_data)
        
        status_text = "opened" if is_open else "closed"
        logger.info(f"Venue {venue_id} {status_text} by user {user_id}")
        
        return {
            "venue_id": venue_id,
            "is_open": is_open,
            "updated_at": update_data['status_updated_at'].isoformat()
        }
    
    async def get_venue_status_info(self, venue_id: str) -> Dict[str, Any]:
        """Get current venue operational status"""
        venue = await self.repo.get_by_id(venue_id)
        if not venue:
            return None
        
        operating_hours = venue.get('operating_hours', [])
        is_open = venue.get('is_open', False)
        is_active = venue.get('is_active', False)
        
        return {
            "venue_id": venue_id,
            "venue_name": venue.get('name'),
            "is_active": is_active,
            "is_open": is_open,
            "current_status": "open" if (is_active and is_open) else "closed",
            "operating_hours": operating_hours,
            "last_updated": venue.get('status_updated_at'),
            "status_reason": venue.get('status_reason')
        }
    
    async def get_control_panel_status(self, venue_id: str) -> Dict[str, Any]:
        """Get simplified venue status for control panel"""
        venue = await self.repo.get_by_id(venue_id)
        if not venue:
            return None
        
        is_open = venue.get('is_open', False)
        is_active = venue.get('is_active', False)
        
        # Create status message
        if is_active and is_open:
            status_message = "Open for Orders"
            status_detail = "Accepting orders"
        elif is_active and not is_open:
            status_message = "Closed"
            status_detail = "Not accepting orders"
        else:
            status_message = "Inactive"
            status_detail = "Venue is inactive"
        
        return {
            "venue_id": venue_id,
            "venue_name": venue.get('name', 'Unknown Venue'),
            "status_message": status_message,
            "status_detail": status_detail,
            "is_open": is_open,
            "is_active": is_active,
            "last_updated": venue.get('status_updated_at'),
            "updated_by": venue.get('status_updated_by')
        }
    
    async def activate_venue(self, venue_id: str, user_id: str) -> bool:
        """Activate venue"""
        await self.repo.update(venue_id, {
            "is_active": True,
            "activated_at": datetime.utcnow(),
            "activated_by": user_id
        })
        
        logger.info(f"Venue activated: {venue_id} by user {user_id}")
        return True
    
    async def deactivate_venue(self, venue_id: str, user_id: str, reason: Optional[str] = None) -> bool:
        """Deactivate venue"""
        update_data = {
            'is_active': False,
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': user_id
        }
        
        if reason:
            update_data['deactivation_reason'] = reason
        
        await self.repo.update(venue_id, update_data)
        
        logger.info(f"Venue deactivated: {venue_id} by user {user_id}")
        return True
    
    async def update_subscription(self, venue_id: str, subscription_plan: str, subscription_status: str) -> bool:
        """Update venue subscription"""
        await self.repo.update(venue_id, {
            "subscription_plan": subscription_plan,
            "subscription_status": subscription_status
        })
        
        logger.info(f"Subscription updated for venue: {venue_id}")
        return True
    
    async def update_operating_hours(self, venue_id: str, operating_hours: List[Dict[str, Any]]) -> bool:
        """Update venue operating hours"""
        await self.repo.update(venue_id, {"operating_hours": operating_hours})
        
        logger.info(f"Operating hours updated for venue: {venue_id}")
        return True
    
    async def fix_all_venue_statuses(self) -> Dict[str, int]:
        """Fix venue status data for all venues"""
        all_venues = await self.repo.get_all()
        
        fixed_count = 0
        for venue in all_venues:
            original_status = venue.get('status')
            cleaned_venue = clean_venue_status(venue.copy())
            new_status = cleaned_venue.get('status')
            
            if original_status != new_status:
                await self.repo.update(venue['id'], {'status': new_status})
                fixed_count += 1
                logger.info(f"Fixed venue {venue['id']} status from {repr(original_status)} to {repr(new_status)}")
        
        logger.info(f"Venue status data maintenance completed. Fixed {fixed_count} venues.")
        
        return {"fixed_count": fixed_count, "total_venues": len(all_venues)}


# Singleton instance
_venue_service = None

def get_venue_service() -> VenueService:
    """Get venue service singleton"""
    global _venue_service
    if _venue_service is None:
        _venue_service = VenueService()
    return _venue_service