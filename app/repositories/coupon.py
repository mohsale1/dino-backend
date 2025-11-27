"""
Coupon Repository
Database operations for coupon management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class CouponRepository(BaseRepository):
    """Repository for coupon operations"""
    
    def __init__(self):
        super().__init__(collection_name="coupons")
    
    async def get_by_code(self, code: str, venue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get coupon by code and venue ID
        
        Args:
            code: Coupon code (case-insensitive)
            venue_id: Venue ID
            
        Returns:
            Coupon data or None
        """
        try:
            # Convert code to uppercase for case-insensitive search
            code_upper = code.strip().upper()
            
            coupons = await self.query([
                ('code', '==', code_upper),
                ('venue_id', '==', venue_id)
            ])
            
            if coupons:
                logger.info(f"Found coupon: {code_upper} for venue: {venue_id}")
                return coupons[0]
            
            logger.info(f"Coupon not found: {code_upper} for venue: {venue_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting coupon by code: {e}", exc_info=True)
            raise
    
    async def get_by_venue(self, venue_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all coupons for a venue
        
        Args:
            venue_id: Venue ID
            include_inactive: Whether to include inactive coupons
            
        Returns:
            List of coupons
        """
        try:
            filters = [('venue_id', '==', venue_id)]
            
            if not include_inactive:
                filters.append(('is_active', '==', True))
            
            coupons = await self.query(filters)
            
            logger.info(f"Found {len(coupons)} coupons for venue: {venue_id}")
            return coupons
            
        except Exception as e:
            logger.error(f"Error getting coupons for venue: {e}", exc_info=True)
            raise
    
    async def get_active_coupons(self, venue_id: str) -> List[Dict[str, Any]]:
        """
        Get all active, non-expired coupons for a venue
        
        Args:
            venue_id: Venue ID
            
        Returns:
            List of active coupons
        """
        try:
            # Get all active coupons
            coupons = await self.get_by_venue(venue_id, include_inactive=False)
            
            # Filter out expired coupons
            now = datetime.utcnow()
            active_coupons = [
                coupon for coupon in coupons
                if coupon.get('expiry_date') and coupon['expiry_date'] > now
            ]
            
            logger.info(f"Found {len(active_coupons)} active coupons for venue: {venue_id}")
            return active_coupons
            
        except Exception as e:
            logger.error(f"Error getting active coupons: {e}", exc_info=True)
            raise
    
    async def increment_usage_count(self, coupon_id: str) -> bool:
        """
        Increment the usage count of a coupon
        
        Args:
            coupon_id: Coupon ID
            
        Returns:
            True if successful
        """
        try:
            coupon = await self.get_by_id(coupon_id)
            if not coupon:
                logger.warning(f"Coupon not found for usage increment: {coupon_id}")
                return False
            
            new_count = coupon.get('usage_count', 0) + 1
            
            await self.update(coupon_id, {
                'usage_count': new_count,
                'updated_at': datetime.utcnow()
            })
            
            logger.info(f"Incremented usage count for coupon {coupon_id}: {new_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing usage count: {e}", exc_info=True)
            raise
    
    async def check_code_exists(self, code: str, venue_id: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if a coupon code already exists for a venue
        
        Args:
            code: Coupon code
            venue_id: Venue ID
            exclude_id: Coupon ID to exclude (for updates)
            
        Returns:
            True if code exists
        """
        try:
            code_upper = code.strip().upper()
            existing = await self.get_by_code(code_upper, venue_id)
            
            if not existing:
                return False
            
            # If excluding an ID (for updates), check if it's a different coupon
            if exclude_id and existing.get('id') == exclude_id:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking code existence: {e}", exc_info=True)
            raise
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all coupons for a workspace
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            List of coupons
        """
        try:
            coupons = await self.query([('workspace_id', '==', workspace_id)])
            logger.info(f"Found {len(coupons)} coupons for workspace: {workspace_id}")
            return coupons
            
        except Exception as e:
            logger.error(f"Error getting coupons for workspace: {e}", exc_info=True)
            raise