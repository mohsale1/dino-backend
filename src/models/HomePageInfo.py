"""
Home Page Info Model
Stores home page data: stats, testimonials, and contact information
"""

from src.base.BaseModel import BaseModel
from typing import Dict, Any, List, Optional


class HomePageInfo(BaseModel):
    """
    Model for home page information
    
    Structure:
    {
        "stats": [
            {
                "title": "Active Restaurants",
                "value": "1",
                "number": 1,
                "suffix": "+",
                "label": "Active Restaurants",
                "icon": "restaurant"
            },
            ...
        ],
        "testimonials": [
            {
                "name": "John Doe",
                "role": "Restaurant Owner",
                "restaurant": "Doe's Diner",
                "location": "New York, NY",
                "rating": 5,
                "comment": "Great platform!",
                "avatar": "JD",
                "created_at": "2024-01-01T00:00:00Z"
            },
            ...
        ],
        "contact": {
            "email": "contact@example.com",
            "phone": "+1234567890",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001"
        }
    }
    """
    
    def __init__(self):
        super().__init__()
        
        # Stats array
        self.stats: List[Dict[str, Any]] = []
        
        # Testimonials array
        self.testimonials: List[Dict[str, Any]] = []
        
        # Contact information
        self.contact: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        data = super().to_dict()
        
        return {
            **data,
            "stats": self.stats,
            "testimonials": self.testimonials,
            "contact": self.contact
        }