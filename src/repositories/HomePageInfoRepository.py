"""
Home Page Info Repository
Handles database operations for home page information
"""

from src.base.BaseRepository import BaseRepository
from typing import Dict, Any, Optional, List


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
        Get the home page info (there should only be one document)
        Returns the first document or None
        
        Note: Validates that the document has the correct structure
        (stats, testimonials, contact keys)
        """
        items = self.get_all(limit=1)
        
        if not items:
            return None
        
        doc = items[0]
        
        # Validate structure - ensure it's not a user document or other wrong data
        required_keys = ['stats', 'testimonials', 'contact']
        invalid_keys = ['password_hash', 'role_id', 'workspace_id', 'organization_id']
        
        # Check for invalid keys (user document in wrong collection)
        if any(key in doc for key in invalid_keys):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Found invalid document in homepage_info collection (ID: {doc.get('id')})")
            logger.error("This appears to be a user document in the wrong collection!")
            logger.error("Please run: python backend/cleanup_homepage_info.py")
            return None
        
        # Check for required keys
        if not all(key in doc for key in required_keys):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Homepage info document missing required keys. Found: {list(doc.keys())}")
        
        return doc
    
    def get_or_create_homepage_info(self) -> Dict[str, Any]:
        """
        Get existing home page info or create default one with proper default values
        """
        existing = self.get_homepage_info()
        
        if existing:
            return existing
        
        # Create default home page info with proper default values
        from datetime import datetime
        
        default_data = {
            # Stats array - default values
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
                    "created_at": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "name": "Priya Sharma",
                    "role": "Manager",
                    "restaurant": "Cafe Coffee Day",
                    "location": "Bangalore, Karnataka",
                    "rating": 5,
                    "comment": "The analytics dashboard gives us incredible insights into our business. We've increased our revenue by 30% since implementing Dino. Best decision ever!",
                    "avatar": "PS",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "name": "Amit Patel",
                    "role": "Owner",
                    "restaurant": "Gujarat Bhavan",
                    "location": "Ahmedabad, Gujarat",
                    "rating": 5,
                    "comment": "Managing multiple outlets was a challenge until we found Dino. Now everything is centralized and efficient. Our staff loves how easy it is to use.",
                    "avatar": "AP",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "name": "Sneha Reddy",
                    "role": "Co-founder",
                    "restaurant": "South Indian Delights",
                    "location": "Hyderabad, Telangana",
                    "rating": 5,
                    "comment": "The QR code ordering system is a game-changer! Our customers can browse the menu and place orders seamlessly. Customer satisfaction has gone up significantly.",
                    "avatar": "SR",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "name": "Vikram Singh",
                    "role": "Owner",
                    "restaurant": "Punjabi Tadka",
                    "location": "Chandigarh, Punjab",
                    "rating": 5,
                    "comment": "Dino helped us go digital without any hassle. The support team is amazing and the platform is very user-friendly. Our business has grown 40% in just 6 months!",
                    "avatar": "VS",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                },
                {
                    "name": "Meera Iyer",
                    "role": "Manager",
                    "restaurant": "Saravana Bhavan",
                    "location": "Chennai, Tamil Nadu",
                    "rating": 5,
                    "comment": "Real-time order tracking and inventory management features are outstanding. We can now serve more customers efficiently and reduce wastage significantly.",
                    "avatar": "MI",
                    "created_at": datetime.utcnow().isoformat() + "Z"
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
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_deleted': False,
            'is_active': True
        }
        
        # Create document
        doc_ref = self.collection.document()
        default_data['id'] = doc_ref.id
        doc_ref.set(default_data)
        
        return self.get_by_id(doc_ref.id)
    
    def update_homepage_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update home page info (creates if doesn't exist)
        Supports partial updates - only updates provided fields
        """
        from datetime import datetime
        
        existing = self.get_homepage_info()
        
        # Add updated timestamp
        data['updated_at'] = datetime.utcnow()
        
        if existing:
            # Merge with existing data for partial updates
            updated_data = {**existing, **data}
            self.update(existing['id'], updated_data)
            return self.get_by_id(existing['id'])
        else:
            # Create new with provided data
            data['created_at'] = datetime.utcnow()
            homepage_id = self.create(data)
            return self.get_by_id(homepage_id)
    
    def update_stats(self, stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update only the stats array
        """
        return self.update_homepage_info({"stats": stats})
    
    def update_testimonials(self, testimonials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update only the testimonials array
        """
        return self.update_homepage_info({"testimonials": testimonials})
    
    def update_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update only the contact information
        """
        return self.update_homepage_info({"contact": contact})
    
    def get_stats(self) -> List[Dict[str, Any]]:
        """
        Get stats array from homepage_info
        """
        info = self.get_or_create_homepage_info()
        return info.get('stats', [])
    
    def get_testimonials(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get testimonials array from homepage_info
        """
        info = self.get_or_create_homepage_info()
        testimonials = info.get('testimonials', [])
        
        if limit and limit > 0:
            return testimonials[:limit]
        
        return testimonials
    
    def get_contact(self) -> Dict[str, Any]:
        """
        Get contact information from homepage_info
        """
        info = self.get_or_create_homepage_info()
        return info.get('contact', {})