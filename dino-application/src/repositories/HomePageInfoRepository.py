"""
Home Page Info Repository
Handles database operations for home page information
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from src.base.BaseRepository import BaseRepository

logger = logging.getLogger(__name__)


class HomePageInfoRepository(BaseRepository):
    """
    Repository for home page information

    Manages a single document containing:
    - stats: array of stat objects
    - testimonials: array of testimonial objects
    - contact: contact information object
    """

    def __init__(self):
        super().__init__("homepage_info")

    def get_homepage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get the home page info (there should only be one document).
        Returns the first document or None.

        Note: Validates that the document has the correct structure
        (stats, testimonials, contact keys).
        """
        items = self.get_all(limit=1)

        if not items:
            return None

        doc = items[0]

        invalid_keys = ['password_hash', 'role_id', 'workspace_id', 'organization_id']
        if any(key in doc for key in invalid_keys):
            logger.error(f"Found invalid document in homepage_info collection (ID: {doc.get('id')})")
            logger.error("This appears to be a user document in the wrong collection!")
            logger.error("Please run: python backend/cleanup_homepage_info.py")
            return None

        required_keys = ['stats', 'testimonials', 'contact']
        if not all(key in doc for key in required_keys):
            logger.warning(f"Homepage info document missing required keys. Found: {list(doc.keys())}")

        return doc

    def get_or_create_homepage_info(self) -> Dict[str, Any]:
        """
        Get existing home page info or create a default one.
        """
        existing = self.get_homepage_info()

        if existing:
            return existing

        now = datetime.now(timezone.utc)

        default_data = {
            'stats': [
                {
                    "title": "Active Restaurants",
                    "value": "1",
                    "number": 1,
                    "suffix": "+",
                    "label": "Active Restaurants",
                    "icon": "restaurant"
                },
                {
                    "title": "Orders Processed",
                    "value": "0",
                    "number": 0,
                    "suffix": "+",
                    "label": "Orders Processed",
                    "icon": "shopping_cart"
                },
                {
                    "title": "Happy Customers",
                    "value": "0",
                    "number": 0,
                    "suffix": "+",
                    "label": "Happy Customers",
                    "icon": "people"
                },
                {
                    "title": "Menu Items",
                    "value": "0",
                    "number": 0,
                    "suffix": "+",
                    "label": "Menu Items",
                    "icon": "menu_book"
                }
            ],
            'testimonials': [
                {
                    "name": "Rajesh Kumar",
                    "role": "Owner",
                    "restaurant": "Spice Garden Restaurant",
                    "location": "Mumbai, Maharashtra",
                    "rating": 5,
                    "comment": "Dino transformed our restaurant operations completely. Orders are faster, more accurate, and our customers love the digital menu experience. Highly recommended!",
                    "avatar": "RK",
                    "created_at": now.isoformat()
                },
                {
                    "name": "Priya Sharma",
                    "role": "Manager",
                    "restaurant": "Cafe Coffee Day",
                    "location": "Bangalore, Karnataka",
                    "rating": 5,
                    "comment": "The analytics dashboard gives us incredible insights into our business. We've increased our revenue by 30% since implementing Dino. Best decision ever!",
                    "avatar": "PS",
                    "created_at": now.isoformat()
                },
                {
                    "name": "Amit Patel",
                    "role": "Owner",
                    "restaurant": "Gujarat Bhavan",
                    "location": "Ahmedabad, Gujarat",
                    "rating": 5,
                    "comment": "Managing multiple outlets was a challenge until we found Dino. Now everything is centralized and efficient. Our staff loves how easy it is to use.",
                    "avatar": "AP",
                    "created_at": now.isoformat()
                },
                {
                    "name": "Sneha Reddy",
                    "role": "Co-founder",
                    "restaurant": "South Indian Delights",
                    "location": "Hyderabad, Telangana",
                    "rating": 5,
                    "comment": "The QR code ordering system is a game-changer! Our customers can browse the menu and place orders seamlessly. Customer satisfaction has gone up significantly.",
                    "avatar": "SR",
                    "created_at": now.isoformat()
                },
                {
                    "name": "Vikram Singh",
                    "role": "Owner",
                    "restaurant": "Punjabi Tadka",
                    "location": "Chandigarh, Punjab",
                    "rating": 5,
                    "comment": "Dino helped us go digital without any hassle. The support team is amazing and the platform is very user-friendly. Our business has grown 40% in just 6 months!",
                    "avatar": "VS",
                    "created_at": now.isoformat()
                },
                {
                    "name": "Meera Iyer",
                    "role": "Manager",
                    "restaurant": "Saravana Bhavan",
                    "location": "Chennai, Tamil Nadu",
                    "rating": 5,
                    "comment": "Real-time order tracking and inventory management features are outstanding. We can now serve more customers efficiently and reduce wastage significantly.",
                    "avatar": "MI",
                    "created_at": now.isoformat()
                }
            ],
            'contact': {
                "email": "contact@dino.restaurant",
                "phone": "+1 (555) 123-4567",
                "address": "123 Restaurant Street",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "postal_code": "94102"
            },
            'created_at': now,
            'updated_at': now,
            'is_deleted': False,
            'is_active': True
        }

        created = self.create(default_data)
        return self.get_by_id(created['id'])

    def update_homepage_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update home page info (creates if doesn't exist).
        Supports partial updates — only the provided fields are written.
        """
        existing = self.get_homepage_info()

        data['updated_at'] = datetime.now(timezone.utc)

        if existing:
            self.update(existing['id'], data)
            return self.get_by_id(existing['id'])
        else:
            data['created_at'] = datetime.now(timezone.utc)
            created = self.create(data)
            return self.get_by_id(created['id'])

    def update_stats(self, stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update only the stats array"""
        return self.update_homepage_info({"stats": stats})

    def update_testimonials(self, testimonials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update only the testimonials array"""
        return self.update_homepage_info({"testimonials": testimonials})

    def update_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Update only the contact information"""
        return self.update_homepage_info({"contact": contact})

    def get_stats(self) -> List[Dict[str, Any]]:
        """Get stats array from homepage_info"""
        info = self.get_or_create_homepage_info()
        return info.get('stats', [])

    def get_testimonials(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get testimonials array from homepage_info"""
        info = self.get_or_create_homepage_info()
        testimonials = info.get('testimonials', [])

        if limit and limit > 0:
            return testimonials[:limit]

        return testimonials

    def get_contact(self) -> Dict[str, Any]:
        """Get contact information from homepage_info"""
        info = self.get_or_create_homepage_info()
        return info.get('contact', {})