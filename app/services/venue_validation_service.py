"""
Venue and Table Validation Service
Handles validation logic for venue status and table existence before showing menu
"""
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from datetime import datetime

from app.core.logging_config import get_logger
from app.core.dependency_injection import get_repository_manager
from app.models.schemas import VenueStatus

logger = get_logger(__name__)


class VenueValidationService:
    """Service for validating venue and table access for public ordering"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
    
    async def validate_venue_and_table_for_menu(
        self, 
        venue_id: str, 
        table_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate venue and table for menu access
        
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, response_data)
            - If valid: (True, {"venue": venue_data, "table": table_data})
            - If invalid: (False, {"error": error_message, "error_type": error_type})
        """
        try:
            # Get repositories
            venue_repo = self.repo_manager.get_repository('venue')
            table_repo = self.repo_manager.get_repository('table')
            
            # 1. Check if venue exists
            venue = await venue_repo.get_by_id(venue_id)
            if not venue:
                return False, {
                    "error": "Venue not found",
                    "error_type": "venue_not_found",
                    "message": "The venue you're trying to access does not exist."
                }
            
            # 2. Check if venue is active
            if not venue.get('is_active', False):
                return False, {
                    "error": "Venue is not accepting orders",
                    "error_type": "venue_inactive",
                    "message": "This venue is currently not accepting orders. Please try again later.",
                    "venue_name": venue.get('name', 'Unknown Venue')
                }
            
            # 3. Check venue status
            venue_status = venue.get('status', VenueStatus.ACTIVE.value)
            if venue_status not in [VenueStatus.ACTIVE.value]:
                return False, {
                    "error": "Venue is not accepting orders",
                    "error_type": "venue_not_operational",
                    "message": "This venue is currently not accepting orders. Please try again later.",
                    "venue_name": venue.get('name', 'Unknown Venue'),
                    "venue_status": venue_status
                }
            
            # 4. If table_id is provided, validate table exists and belongs to venue
            table_data = None
            if table_id:
                table = await table_repo.get_by_id(table_id)
                if not table:
                    return False, {
                        "error": "Table not found",
                        "error_type": "table_not_found",
                        "message": "The table you're trying to access does not exist."
                    }
                
                # Check if table belongs to the venue
                if table.get('venue_id') != venue_id:
                    return False, {
                        "error": "Table does not belong to this venue",
                        "error_type": "table_venue_mismatch",
                        "message": "The table you're trying to access does not belong to this venue."
                    }
                
                # Check if table is active
                if not table.get('is_active', False):
                    return False, {
                        "error": "Table is not available",
                        "error_type": "table_inactive",
                        "message": "This table is currently not available for orders."
                    }
                
                table_data = {
                    "id": table['id'],
                    "table_number": table.get('table_number'),
                    "capacity": table.get('capacity', 4),
                    "location": table.get('location'),
                    "status": table.get('table_status')
                }
            
            # All validations passed
            venue_data = {
                "id": venue['id'],
                "name": venue['name'],
                "description": venue.get('description', ''),
                "location": venue.get('location', {}),
                "phone": venue.get('phone', ''),
                "email": venue.get('email'),
                "is_active": venue.get('is_active', False),
                "is_open": venue.get('is_open', False),
                "status": venue.get('status', VenueStatus.ACTIVE.value),
                "rating": self._calculate_venue_rating(venue)
            }
            
            return True, {
                "venue": venue_data,
                "table": table_data,
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating venue and table: {e}")
            return False, {
                "error": "Validation failed",
                "error_type": "validation_error",
                "message": "Unable to validate venue and table access. Please try again."
            }
    
    async def validate_qr_code_access(self, qr_code: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate QR code and return venue/table information if valid
        
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, response_data)
        """
        try:
            # Get table repository to find table by QR code
            table_repo = self.repo_manager.get_repository('table')
            
            # Find table by QR code
            tables = await table_repo.query([('qr_code', '==', qr_code)])
            if not tables:
                return False, {
                    "error": "Invalid QR code",
                    "error_type": "invalid_qr_code",
                    "message": "The QR code you scanned is not valid or has expired."
                }
            
            table = tables[0]
            venue_id = table.get('venue_id')
            table_id = table.get('id')
            
            # Validate venue and table
            is_valid, validation_data = await self.validate_venue_and_table_for_menu(
                venue_id, table_id
            )
            
            if not is_valid:
                return False, validation_data
            
            # Add QR code specific data
            validation_data['qr_code'] = qr_code
            validation_data['access_method'] = 'qr_scan'
            
            return True, validation_data
            
        except Exception as e:
            logger.error(f"Error validating QR code access: {e}")
            return False, {
                "error": "QR code validation failed",
                "error_type": "qr_validation_error",
                "message": "Unable to validate QR code. Please try again."
            }
    
    def _calculate_venue_rating(self, venue: Dict[str, Any]) -> float:
        """Calculate venue average rating"""
        rating_total = venue.get('rating_total', 0.0)
        rating_count = venue.get('rating_count', 0)
        
        if rating_count == 0:
            return 0.0
        
        return round(rating_total / rating_count, 2)
    
    async def check_venue_operating_status(self, venue_id: str) -> Dict[str, Any]:
        """
        Check if venue is currently open for orders
        Enhanced version of the method from public_ordering_service
        """
        try:
            venue_repo = self.repo_manager.get_repository('venue')
            venue = await venue_repo.get_by_id(venue_id)
            
            if not venue:
                return {
                    'current_status': 'closed',
                    'is_open': False,
                    'message': 'Venue not found',
                    'error_type': 'venue_not_found'
                }
            
            # Check if venue is active
            is_active = venue.get('is_active', False)
            venue_status = venue.get('status', VenueStatus.ACTIVE.value)
            
            # Venue is operational if it's active, open, and has active status
            is_operational = (
                is_active and 
                venue_status == VenueStatus.ACTIVE.value
            )
            
            if not is_operational:
                return {
                    'message': 'Venue is currently not accepting orders',
                    'error_type': 'venue_not_operational',
                    'venue_name': venue.get('name', 'Unknown Venue'),
                    'venue_status': venue_status,
                    'is_active': is_active
                }
            
            return {
                'current_status': 'open',
                'is_open': True,
                'message': 'Venue is open for orders',
                'venue_name': venue.get('name', 'Unknown Venue'),
                'venue_status': venue_status,
                'is_active': is_active,
                'next_opening': None,  # Would be calculated based on operating hours
                'next_closing': None   # Would be calculated based on operating hours
            }
            
        except Exception as e:
            logger.error(f"Error checking venue status {venue_id}: {e}")
            return {
                'current_status': 'unknown',
                'is_open': False,
                'message': 'Unable to check venue status',
                'error_type': 'status_check_error'
            }


# Singleton instance
venue_validation_service = VenueValidationService()