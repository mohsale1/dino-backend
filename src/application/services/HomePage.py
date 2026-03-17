"""
Home Page Service
Provides data for the public home page from homepage_info collection
"""

from typing import Dict, Any, List, Optional
from src.repositories.HomePageInfoRepository import HomePageInfoRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.OrderRepository import OrderRepository


class HomePageService:
    """
    Service for home page data
    
    All data is stored in and retrieved from the homepage_info collection.
    This collection contains:
    - stats: array of stat objects
    - testimonials: array of testimonial objects
    - contact: contact information object
    """
    
    def __init__(self):
        self.homepage_repo = HomePageInfoRepository()
        self.workspace_repo = WorkspaceRepository()
        self.order_repo = OrderRepository()
    
    def get_stats(self) -> List[Dict[str, Any]]:
        """
        Get home page statistics with real-time data from database
        
        Dynamically calculates:
        - Active Businesses: Count of active workspaces
        - Orders Processed: Total count of all orders
        
        Falls back to database default values if calculation fails.
        
        Returns:
            List of stat objects with structure:
            {
                "title": "Active Businesses",
                "value": "50",
                "number": 50,
                "suffix": "+",
                "label": "Active Businesses",
                "icon": "business"
            }
        """
        try:
            # Get stats from database (default values)
            default_stats = self.homepage_repo.get_stats()
            
            # Calculate real-time values
            try:
                # Count active workspaces
                active_workspaces = self.workspace_repo.get_all(filters={'is_active': True, 'is_deleted': False})
                workspace_count = len(active_workspaces)
                
                # Count total orders
                all_orders = self.order_repo.get_all(filters={'is_deleted': False})
                order_count = len(all_orders)
                
                # Update stats with real-time values
                updated_stats = []
                for stat in default_stats:
                    stat_copy = stat.copy()
                    
                    # Update Active Businesses stat
                    if stat.get('title') == 'Active Businesses' or stat.get('label') == 'Active Businesses':
                        stat_copy['number'] = workspace_count
                        stat_copy['value'] = str(workspace_count)
                    
                    # Update Orders Processed stat
                    elif stat.get('title') == 'Orders Processed' or stat.get('label') == 'Orders Processed':
                        stat_copy['number'] = order_count
                        # Format large numbers (e.g., 10000 -> 10K, 1000000 -> 1M)
                        if order_count >= 1000000:
                            stat_copy['value'] = f"{order_count / 1000000:.1f}M"
                        elif order_count >= 1000:
                            stat_copy['value'] = f"{order_count / 1000:.1f}K"
                        else:
                            stat_copy['value'] = str(order_count)
                    
                    updated_stats.append(stat_copy)
                
                return updated_stats
                
            except Exception as calc_error:
                # If calculation fails, return default stats from database
                print(f"Error calculating real-time stats, using defaults: {calc_error}")
                return default_stats
                
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return []

    
    def get_testimonials(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get customer testimonials from homepage_info collection
        
        Args:
            limit: Maximum number of testimonials to return
            
        Returns:
            List of testimonial objects with structure:
            {
                "name": "John Doe",
                "role": "Restaurant Owner",
                "restaurant": "Doe's Diner",
                "location": "New York, NY",
                "rating": 5,
                "comment": "Great platform!",
                "avatar": "JD",
                "created_at": "2024-01-01T00:00:00Z"
            }
        """
        try:
            return self.homepage_repo.get_testimonials(limit=limit)
        except Exception as e:
            print(f"Error fetching testimonials: {e}")
            return []
    
    def get_contact_info(self) -> Dict[str, Any]:
        """
        Get contact information from homepage_info collection
        
        Returns:
            Contact object with structure:
            {
                "email": "contact@example.com",
                "phone": "+1234567890",
                "address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001"
            }
        """
        try:
            return self.homepage_repo.get_contact()
        except Exception as e:
            print(f"Error fetching contact info: {e}")
            return {}

    
    def get_all_home_data(self) -> Dict[str, Any]:
        """
        Get all home page data in one call with real-time stats
        
        Returns:
            {
                "stats": [...],  # With real-time calculated values
                "testimonials": [...],
                "contact": {...}
            }
        """
        try:
            homepage_info = self.homepage_repo.get_or_create_homepage_info()
            
            # Get stats with real-time calculations
            stats = self.get_stats()
            
            return {
                "stats": stats,  # Use calculated stats instead of database stats
                "testimonials": homepage_info.get('testimonials', []),
                "contact": homepage_info.get('contact', {})
            }
        except Exception as e:
            print(f"Error fetching all home data: {e}")
            return {
                "stats": [],
                "testimonials": [],
                "contact": {}
            }


    
    # ========================================================================
    # UPDATE METHODS
    # ========================================================================
    
    def update_stats(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update stats array in homepage_info collection
        
        Args:
            stats: Array of stat objects
            
        Returns:
            Updated stats array
        """
        try:
            result = self.homepage_repo.update_stats(stats)
            return result.get('stats', [])
        except Exception as e:
            print(f"Error updating stats: {e}")
            raise ValueError(f"Failed to update stats: {str(e)}")
    
    def update_testimonials(self, testimonials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update testimonials array in homepage_info collection
        
        Args:
            testimonials: Array of testimonial objects
            
        Returns:
            Updated testimonials array
        """
        try:
            result = self.homepage_repo.update_testimonials(testimonials)
            return result.get('testimonials', [])
        except Exception as e:
            print(f"Error updating testimonials: {e}")
            raise ValueError(f"Failed to update testimonials: {str(e)}")
    
    def update_contact_info(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update contact information in homepage_info collection
        
        Args:
            contact_data: Contact information object
            
        Returns:
            Updated contact object
        """
        try:
            result = self.homepage_repo.update_contact(contact_data)
            return result.get('contact', {})
        except Exception as e:
            print(f"Error updating contact info: {e}")
            raise ValueError(f"Failed to update contact information: {str(e)}")
    
    def update_all_homepage_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update entire homepage_info document
        
        Args:
            data: Dictionary containing stats, testimonials, and/or contact
            
        Returns:
            Updated homepage_info document
        """
        try:
            result = self.homepage_repo.update_homepage_info(data)
            return {
                "stats": result.get('stats', []),
                "testimonials": result.get('testimonials', []),
                "contact": result.get('contact', {})
            }
        except Exception as e:
            print(f"Error updating homepage data: {e}")
            raise ValueError(f"Failed to update homepage data: {str(e)}")
