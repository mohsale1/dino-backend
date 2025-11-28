"""
Validation Service
Provides comprehensive validation for user data, business rules, data integrity,
and venue/table validation for public ordering
"""
from typing import Dict, List, Any, Optional, Tuple
from fastapi import HTTPException, status
import re
from datetime import datetime

from app.core.logging import get_logger
from app.core.dependencies import get_repository_manager
from app.models.entities import VenueStatus

logger = get_logger(__name__)


class ValidationService:
    """Service for validating user data, business rules, and venue/table access"""
    
    def __init__(self):
        # Use centralized validation from security module
        from app.core.security import security_validator
        self.security_validator = security_validator
        self.mobile_pattern = re.compile(r'^[0-9]{10}$') 
        self.repo_manager = get_repository_manager()
    
    async def validate_user_data(self, user_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate user data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Email validation
        email = user_data.get('email', '').strip().lower()
        if not is_update or email:  # Required for creation, optional for update
            if not email:
                errors.append("Email is required")
            elif not self.security_validator.validate_email(email):
                errors.append("Invalid email format")
            else:
                # Check email uniqueness
                if not is_update:
                    existing_user = await self._check_email_exists(email)
                    if existing_user:
                        errors.append("Email already exists")
        
        # Phone number validation
        mobile = user_data.get('phone', '').strip()
        if mobile:
            if not self.mobile_pattern.match(mobile):
                errors.append("Invalid phone number format")
            else:
                # Check phone uniqueness
                if not is_update:
                    existing_phone = await self._check_phone_exists(mobile)
                    if existing_phone:
                        errors.append("Phone number already exists")
        
        # Password validation (only for creation or when password is being updated)
        password = user_data.get('password')
        if password:
            # Use centralized password validation
            validation_result = self.security_validator.validate_password_strength(password)
            if not validation_result['is_valid']:
                errors.extend(validation_result['errors'])
        elif not is_update:
            errors.append("Password is required")
        
        # Confirm password validation removed - handled by UI
        
        # Name validation
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        
        if not is_update or first_name is not None:
            if not first_name:
                errors.append("First name is required")
            elif len(first_name) < 2:
                errors.append("First name must be at least 2 characters long")
        
        if not is_update or last_name is not None:
            if not last_name:
                errors.append("Last name is required")
            elif len(last_name) < 2:
                errors.append("Last name must be at least 2 characters long")
        
        return errors
    
    async def validate_venue_data(self, venue_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate venue data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Name validation
        name = venue_data.get('name', '').strip()
        if not is_update or name is not None:
            if not name:
                errors.append("Venue name is required")
            elif len(name) < 2:
                errors.append("Venue name must be at least 2 characters long")
        
        # Email validation (if provided)
        email = venue_data.get('email', '').strip().lower()
        if email and not self.security_validator.validate_email(email):
            errors.append("Invalid venue email format")
        
        # Phone validation (if provided)
        phone = venue_data.get('phone', '').strip()
        if phone and not self.mobile_pattern.match(phone):
            errors.append("Invalid venue phone number format")
        
        # Location validation
        location = venue_data.get('location', {})
        if not is_update or location:
            if not isinstance(location, dict):
                errors.append("Location must be an object")
            else:
                address = location.get('address', '').strip()
                if not address:
                    errors.append("Venue address is required")
        
        return errors
    
    async def validate_workspace_data(self, workspace_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate workspace data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Display name validation
        display_name = workspace_data.get('display_name', '').strip()
        if not is_update or display_name is not None:
            if not display_name:
                errors.append("Workspace display name is required")
            elif len(display_name) < 2:
                errors.append("Workspace display name must be at least 2 characters long")
        
        # Description validation
        description = workspace_data.get('description', '').strip()
        if description and len(description) > 500:
            errors.append("Workspace description must be less than 500 characters")
        
        return errors
    
    async def validate_menu_item_data(self, menu_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate menu item data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Name validation
        name = menu_data.get('name', '').strip()
        if not is_update or name is not None:
            if not name:
                errors.append("Menu item name is required")
            elif len(name) < 2:
                errors.append("Menu item name must be at least 2 characters long")
        
        # Price validation
        price = menu_data.get('price')
        if not is_update or price is not None:
            if price is None:
                errors.append("Price is required")
            elif not isinstance(price, (int, float)) or price < 0:
                errors.append("Price must be a positive number")
        
        # Category validation
        category_id = menu_data.get('category_id', '').strip()
        if not is_update or category_id is not None:
            if not category_id:
                errors.append("Category is required")
        
        return errors
    
    async def validate_order_data(self, order_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate order data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Items validation
        items = order_data.get('items', [])
        if not is_update or items is not None:
            if not items:
                errors.append("Order must contain at least one item")
            elif not isinstance(items, list):
                errors.append("Order items must be a list")
            else:
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append(f"Order item {i+1} must be an object")
                        continue
                    
                    if not item.get('menu_item_id'):
                        errors.append(f"Order item {i+1} must have a menu_item_id")
                    
                    quantity = item.get('quantity')
                    if not isinstance(quantity, int) or quantity <= 0:
                        errors.append(f"Order item {i+1} quantity must be a positive integer")
        
        # Table validation
        table_id = order_data.get('table_id', '').strip()
        if not is_update or table_id is not None:
            if not table_id:
                errors.append("Table ID is required")
        
        return errors
    
    async def _check_email_exists(self, email: str) -> bool:
        """Check if email already exists in the system"""
        try:
            from app.database.repository_manager import get_user_repo
            user_repo = get_user_repo()
            existing_user = await user_repo.get_by_email(email)
            return existing_user is not None
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
    
    async def _check_phone_exists(self, phone: str) -> bool:
        """Check if phone number already exists in the system"""
        try:
            from app.database.repository_manager import get_user_repo
            user_repo = get_user_repo()
            existing_user = await user_repo.get_by_phone(phone)
            return existing_user is not None
        except Exception as e:
            logger.error(f"Error checking phone existence: {e}")
            return False
    
    def raise_validation_exception(self, errors: List[str]):
        """Raise HTTPException with validation errors"""
        from app.core.utils import raise_validation_error
        if errors:
            # Use centralized validation error raising
            raise_validation_error([], custom_message=f"Validation failed: {'; '.join(errors)}")
    
    def validate_email_format(self, email: str) -> bool:
        """Validate email format - delegates to security_validator"""
        return self.security_validator.validate_email(email.strip().lower())
    
    def validate_phone_format(self, phone: str) -> bool:
        """Validate phone number format"""
        return bool(self.mobile_pattern.match(phone.strip()))
    
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength - delegates to security_validator"""
        result = self.security_validator.validate_password_strength(password)
        return result['is_valid']
    
    async def validate_business_rules(self, entity_type: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> List[str]:
        """
        Validate business rules for different entity types
        """
        errors = []
        context = context or {}
        
        if entity_type == "user_role_assignment":
            # Validate role assignment rules
            role_name = data.get('role_name', '').lower()
            venue_id = data.get('venue_id')
            
            if role_name in ['admin', 'operator'] and not venue_id:
                errors.append("Admin and Operator roles require a venue assignment")
            
            # Check if user already has a role in this venue
            user_id = data.get('user_id')
            if user_id and venue_id:
                existing_role = await self._check_user_venue_role(user_id, venue_id)
                if existing_role:
                    errors.append(f"User already has role '{existing_role}' in this venue")
        
        elif entity_type == "venue_capacity":
            # Validate venue capacity rules
            max_tables = data.get('max_tables', 0)
            current_tables = context.get('current_tables', 0)
            
            if max_tables < current_tables:
                errors.append(f"Cannot reduce max tables below current table count ({current_tables})")
        
        elif entity_type == "order_timing":
            # Validate order timing rules
            venue_id = data.get('venue_id')
            if venue_id:
                is_open = await self._check_venue_operating_hours(venue_id)
                if not is_open:
                    errors.append("Venue is currently closed for orders")
        
        return errors
    
    async def _check_user_venue_role(self, user_id: str, venue_id: str) -> Optional[str]:
        """Check if user already has a role in the venue"""
        try:
            from app.database.repository_manager import get_user_repo
            user_repo = get_user_repo()
            user = await user_repo.get_by_id(user_id)
            
            if user and user.get('venue_id') == venue_id:
                # Get role name from role_id
                role_id = user.get('role_id')
                if role_id:
                    from app.database.repository_manager import get_role_repo
                    role_repo = get_role_repo()
                    role = await role_repo.get_by_id(role_id)
                    return role.get('name') if role else None
            
            return None
        except Exception as e:
            logger.error(f"Error checking user venue role: {e}")
            return None
    
    async def _check_venue_operating_hours(self, venue_id: str) -> bool:
        """Check if venue is currently open"""
        try:
            from app.database.repository_manager import get_venue_repo
            venue_repo = get_venue_repo()
            venue = await venue_repo.get_by_id(venue_id)
            
            if not venue or not venue.get('is_active'):
                return False
            
            # Simple check - in a real implementation, you'd check operating hours
            # against current time and day of week
            operating_hours = venue.get('operating_hours', [])
            if not operating_hours:
                return True  # Assume open if no hours specified
            
            # For now, just return True - implement proper time checking as needed
            return True
            
        except Exception as e:
            logger.error(f"Error checking venue operating hours: {e}")
            return False
    
    # =========================================================================
    # VENUE AND TABLE VALIDATION (merged from venue_validation_service)
    # =========================================================================
    
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
            
            # 3. Check venue status and is_open
            venue_status = venue.get('status', VenueStatus.ACTIVE.value)
            is_open = venue.get('is_open')
            
            # Check if venue status is operational
            if venue_status not in [VenueStatus.ACTIVE.value, 'active', 'open']:
                return False, {
                    "error": "Venue is not accepting orders",
                    "error_type": "venue_not_operational",
                    "message": "This venue is currently not accepting orders. Please try again later.",
                    "venue_name": venue.get('name', 'Unknown Venue'),
                    "venue_status": venue_status
                }
            
            # Check if venue is explicitly closed (is_open = False)
            if is_open is False:
                return False, {
                    "error": "Venue is not accepting orders",
                    "error_type": "venue_closed",
                    "message": "This venue is currently closed. Please try again later.",
                    "venue_name": venue.get('name', 'Unknown Venue'),
                    "is_open": is_open
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
        Enhanced version for public ordering
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
            is_open = venue.get('is_open')  # Can be True, False, or None
            venue_status = venue.get('status', VenueStatus.ACTIVE.value)
            
            # Venue is operational if it's active
            # Note: is_open is optional - if not explicitly set to False, we assume venue is open if active
            # status field should be 'active' or match VenueStatus.ACTIVE
            is_operational = (
                is_active and 
                (is_open is not False) and  # Only reject if explicitly False
                venue_status in [VenueStatus.ACTIVE.value, 'active', 'open']
            )
            
            if not is_operational:
                return {
                    'current_status': 'closed',
                    'is_open': False,
                    'message': 'Venue is currently not accepting orders',
                    'error_type': 'venue_not_operational',
                    'venue_name': venue.get('name', 'Unknown Venue'),
                    'venue_status': venue_status,
                    'is_active': is_active,
                    'is_open': is_open
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


# Global instance
_validation_service = None


def get_validation_service() -> ValidationService:
    """Get validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service


# Compatibility alias for venue validation (merged from venue_validation_service)
venue_validation_service = get_validation_service()