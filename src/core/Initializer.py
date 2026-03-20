"""
Application Initialization Module

This module handles automatic initialization of critical system resources
when the application starts, including the SuperAdmin role.
"""

import logging
from typing import Dict, Any
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository
from src.config.Settings import settings

logger = logging.getLogger(__name__)


class ApplicationInitializer:
    """Handles application startup initialization"""
    
    def __init__(self):
        self.role_repository = RoleRepository()
        self.user_repository = UserRepository("system_users")
    
    async def initialize(self):
        """
        Initialize all critical system resources
        
        This method is called during application startup and ensures
        that essential system resources are created.
        """
        logger.info("Starting application initialization...")
        
        try:
            # Initialize SuperAdmin role
            superadmin_role = await self._initialize_superadmin_role()
            
            # Initialize default SuperAdmin user
            if settings.CREATE_DEFAULT_SUPERADMIN and superadmin_role:
                await self._initialize_superadmin_user(superadmin_role)
            
            # Initialize homepage info with default values
            await self._initialize_homepage_info()
            
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during application initialization: {e}", exc_info=True)
            # Don't raise - allow application to start even if initialization fails
            logger.warning("Application will continue despite initialization errors")
    
    async def _initialize_superadmin_role(self):
        """
        Initialize SuperAdmin role
        
        This role is created automatically on application startup and is
        required for all role management operations.
        """
        logger.info("Initializing SuperAdmin role...")
        
        superadmin_name = "SuperAdmin"
        superadmin_type = 0  # System role
        
        try:
            # Check if SuperAdmin role already exists
            existing_role = self.role_repository.get_by_name_and_type(
                superadmin_name,
                superadmin_type
            )
            
            if existing_role:
                logger.info(f"SuperAdmin role already exists (ID: {existing_role.get('id')})")
                return existing_role
            
            # Create SuperAdmin role
            logger.info("Creating SuperAdmin role...")
            
            superadmin_data = {
                'name': superadmin_name,
                'role_type': superadmin_type,
                'description': 'Unrestricted access to the entire system — all APIs, all modules, all administrative operations including user password management, billing, registration codes, and role/permission management.',
            }
            
            created_role = self.role_repository.create(superadmin_data)
            role_id = created_role.get('id')
            
            logger.info(f"SuperAdmin role created successfully (ID: {role_id})")
            
            return created_role
            
        except Exception as e:
            logger.error(f"Failed to initialize SuperAdmin role: {e}", exc_info=True)
            raise
    
    async def _initialize_superadmin_user(self, superadmin_role: Dict[str, Any]):
        """
        Initialize default SuperAdmin user
        
        Creates a default SuperAdmin user with credentials from settings.
        This user is created only once on first startup.
        If user already exists, it will be skipped.
        """
        logger.info("Initializing SuperAdmin user...")
        
        try:
            superadmin_email = settings.SUPERADMIN_EMAIL
            superadmin_password = settings.SUPERADMIN_PASSWORD
            superadmin_role_id = superadmin_role.get('id')
            
            if not superadmin_role_id:
                logger.error("SuperAdmin role ID not found")
                return None
            
            # Check if SuperAdmin user already exists
            existing_users = self.user_repository.get_all(filters={"email": superadmin_email})
            
            if existing_users:
                logger.info(f"SuperAdmin user already exists (Email: {superadmin_email})")
                
                # Verify the user has the correct role
                existing_user = existing_users[0]
                if existing_user.get('role_id') != superadmin_role_id:
                    logger.info("Updating existing user's role to SuperAdmin")
                    self.user_repository.update(
                        existing_user.get('id'),
                        {'role_id': superadmin_role_id}
                    )
                    logger.info("User role updated to SuperAdmin")
                
                return existing_user
            
            # Hash the password
            from src.core.Security import get_password_hash
            
            try:
                password_hash = get_password_hash(superadmin_password)
            except Exception as hash_error:
                logger.error(f"Failed to hash password: {hash_error}")
                raise
            
            # Create SuperAdmin user
            logger.info("Creating SuperAdmin user...")
            
            user_data = {
                'email': superadmin_email,
                'password_hash': password_hash,
                'role_id': superadmin_role_id,
                'is_active': True,
            }
            
            created_user = self.user_repository.create_system_user(user_data)
            user_id = created_user.get('id')
            
            logger.info("=" * 70)
            logger.info("SuperAdmin user created successfully!")
            logger.info("=" * 70)
            logger.info(f"  User ID: {user_id}")
            logger.info(f"  Email: {superadmin_email}")
            logger.info(f"  Role: SuperAdmin")
            logger.info("=" * 70)
            logger.info("You can now login with:")
            logger.info(f"  Email: {superadmin_email}")
            logger.info("  Password: [set via SUPERADMIN_PASSWORD environment variable]")
            logger.info("=" * 70)
            
            return created_user
            
        except Exception as e:
            logger.error(f"Failed to initialize SuperAdmin user: {e}", exc_info=True)
            logger.warning("SuperAdmin user was not created")
            return None
    
    async def _initialize_homepage_info(self):
        """
        Initialize homepage information with default values
        
        Creates the homepage_info collection with default structure:
        - stats: array of stat objects
        - testimonials: array of testimonial objects
        - contact: contact information object
        """
        logger.info("Initializing homepage information...")
        
        try:
            from src.repositories.HomePageInfoRepository import HomePageInfoRepository
            from datetime import datetime, timezone
            
            repo = HomePageInfoRepository()
            
            # Check if homepage info already exists
            existing_info = repo.get_homepage_info()
            
            if existing_info:
                logger.info("Homepage information already exists")
                return existing_info
            
            # Create default homepage info
            logger.info("Creating default homepage information...")
            
            default_data = {
                # Stats array - default values
                'stats': [
                    {
                        "title": "Active Businesses",
                        "value": "50",
                        "number": 50,
                        "suffix": "+",
                        "label": "Active Businesses",
                        "icon": "business"
                    },
                    {
                        "title": "Orders Processed",
                        "value": "10000",
                        "number": 10000,
                        "suffix": "+",
                        "label": "Orders Processed",
                        "icon": "shopping_cart"
                    },
                    {
                        "title": "Customer Satisfaction",
                        "value": "98",
                        "number": 98,
                        "suffix": "%",
                        "label": "Customer Satisfaction",
                        "icon": "sentiment_satisfied"
                    },
                    {
                        "title": "Uptime",
                        "value": "99.9",
                        "number": 99.9,
                        "suffix": "%",
                        "label": "Uptime",
                        "icon": "cloud_done"
                    }
                ],
                
                # Testimonials array - default Indian business reviews
                'testimonials': [
                    {
                        "name": "Rajesh Kumar",
                        "role": "Owner",
                        "restaurant": "Spice Garden Restaurant",
                        "location": "Mumbai, Maharashtra",
                        "rating": 5,
                        "comment": "Dino transformed our restaurant operations completely. Orders are faster, more accurate, and our customers love the digital menu experience. Highly recommended!",
                        "avatar": "RK",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    },
                    {
                        "name": "Priya Sharma",
                        "role": "Manager",
                        "restaurant": "Cafe Coffee Day",
                        "location": "Bangalore, Karnataka",
                        "rating": 5,
                        "comment": "The analytics dashboard gives us incredible insights into our business. We've increased our revenue by 30% since implementing Dino. Best decision ever!",
                        "avatar": "PS",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    },
                    {
                        "name": "Amit Patel",
                        "role": "Owner",
                        "restaurant": "Gujarat Bhavan",
                        "location": "Ahmedabad, Gujarat",
                        "rating": 5,
                        "comment": "Managing multiple outlets was a challenge until we found Dino. Now everything is centralized and efficient. Our staff loves how easy it is to use.",
                        "avatar": "AP",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    },
                    {
                        "name": "Sneha Reddy",
                        "role": "Co-founder",
                        "restaurant": "South Indian Delights",
                        "location": "Hyderabad, Telangana",
                        "rating": 5,
                        "comment": "The QR code ordering system is a game-changer! Our customers can browse the menu and place orders seamlessly. Customer satisfaction has gone up significantly.",
                        "avatar": "SR",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    },
                    {
                        "name": "Vikram Singh",
                        "role": "Owner",
                        "restaurant": "Punjabi Tadka",
                        "location": "Chandigarh, Punjab",
                        "rating": 5,
                        "comment": "Dino helped us go digital without any hassle. The support team is amazing and the platform is very user-friendly. Our business has grown 40% in just 6 months!",
                        "avatar": "VS",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    },
                    {
                        "name": "Meera Iyer",
                        "role": "Manager",
                        "restaurant": "Saravana Bhavan",
                        "location": "Chennai, Tamil Nadu",
                        "rating": 5,
                        "comment": "Real-time order tracking and inventory management features are outstanding. We can now serve more customers efficiently and reduce wastage significantly.",
                        "avatar": "MI",
                        "created_at": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                ],
                
                # Contact information
                'contact': {
                    "email": "contact@dino.restaurant",
                    "phone": "+1 (555) 123-4567",
                    "address": "123 Restaurant Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "United States",
                    "postal_code": "94102"
                },
                
                # Metadata
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'is_deleted': False
            }
            
            created_homepage = repo.create(default_data)
            homepage_id = created_homepage.get('id')
            
            logger.info(f"Homepage information created successfully (ID: {homepage_id})")
            
            return repo.get_by_id(homepage_id)
            
        except Exception as e:
            logger.error(f"Failed to initialize homepage information: {e}", exc_info=True)
            logger.warning("Homepage information was not created")
            return None



# Global initializer instance
_initializer = None


def get_initializer() -> ApplicationInitializer:
    """Get or create the global initializer instance"""
    global _initializer
    if _initializer is None:
        _initializer = ApplicationInitializer()
    return _initializer


async def initialize_application():
    """
    Initialize the application
    
    This function should be called during application startup (in lifespan).
    It ensures all critical system resources are created.
    """
    initializer = get_initializer()
    await initializer.initialize()
