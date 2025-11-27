"""
Query Builder Utility
Centralized query construction and filtering logic
"""
from typing import List, Dict, Any, Optional, Tuple


class QueryBuilder:
    """Centralized query builder for database operations"""
    
    @staticmethod
    def build_filters(
        filters: Optional[Dict[str, Any]] = None,
        exclude_none: bool = True
    ) -> List[Tuple[str, str, Any]]:
        """
        Build query filters from dictionary
        
        Args:
            filters: Dictionary of field: value pairs
            exclude_none: Whether to exclude None values
            
        Returns:
            List of filter tuples (field, operator, value)
        """
        if not filters:
            return []
        
        query_filters = []
        for field, value in filters.items():
            if exclude_none and value is None:
                continue
            query_filters.append((field, '==', value))
        
        return query_filters
    
    @staticmethod
    def add_workspace_filter(
        filters: List[Tuple[str, str, Any]],
        workspace_id: Optional[str],
        user_role: str
    ) -> List[Tuple[str, str, Any]]:
        """
        Add workspace filter for non-admin users
        
        Args:
            filters: Existing filters
            workspace_id: Workspace ID to filter by
            user_role: User's role
            
        Returns:
            Updated filters list
        """
        if user_role not in ['admin', 'superadmin'] and workspace_id:
            filters.append(('workspace_id', '==', workspace_id))
        
        return filters
    
    @staticmethod
    def add_venue_filter(
        filters: List[Tuple[str, str, Any]],
        venue_ids: List[str],
        user_role: str
    ) -> List[Tuple[str, str, Any]]:
        """
        Add venue filter for non-admin users
        
        Args:
            filters: Existing filters
            venue_ids: List of venue IDs user has access to
            user_role: User's role
            
        Returns:
            Updated filters list
        """
        if user_role not in ['admin', 'superadmin'] and venue_ids:
            # Note: Firestore doesn't support 'in' operator with other filters
            # This is a simplified version - may need adjustment based on use case
            if len(venue_ids) == 1:
                filters.append(('venue_id', '==', venue_ids[0]))
        
        return filters
    
    @staticmethod
    def apply_search_filter(
        data: List[Dict[str, Any]],
        search: Optional[str],
        search_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Apply text search filter to data
        
        Args:
            data: List of data dictionaries
            search: Search term
            search_fields: Fields to search in
            
        Returns:
            Filtered data list
        """
        if not search or not search_fields:
            return data
        
        search_lower = search.lower()
        filtered_data = []
        
        for item in data:
            for field in search_fields:
                field_value = item.get(field, "")
                if isinstance(field_value, str) and search_lower in field_value.lower():
                    filtered_data.append(item)
                    break
        
        return filtered_data
    
    @staticmethod
    def paginate(
        data: List[Any],
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Paginate a list of data
        
        Args:
            data: List of data to paginate
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Tuple of (paginated_data, pagination_info)
        """
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        pagination_info = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        return paginated_data, pagination_info
    
    @staticmethod
    def build_search_query(
        base_filters: List[Tuple[str, str, Any]],
        search: Optional[str],
        search_fields: Optional[List[str]] = None
    ) -> List[Tuple[str, str, Any]]:
        """
        Build complete query with search
        
        Args:
            base_filters: Base query filters
            search: Search term
            search_fields: Fields to search (not used in Firestore filters)
            
        Returns:
            Complete query filters
            
        Note:
            Firestore doesn't support text search in queries.
            Search must be applied post-query using apply_search_filter
        """
        # Return base filters as-is
        # Text search must be done in-memory after fetching
        return base_filters


# Global instance
query_builder = QueryBuilder()


# Convenience functions
def build_filters(filters: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str, Any]]:
    """Build query filters - convenience function"""
    return query_builder.build_filters(filters)


def paginate_list(
    data: List[Any],
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Any], Dict[str, Any]]:
    """Paginate list - convenience function"""
    return query_builder.paginate(data, page, page_size)


def apply_search_filter(
    data: List[Dict[str, Any]],
    search: str,
    search_fields: List[str]
) -> List[Dict[str, Any]]:
    """Apply search filter - convenience function"""
    return query_builder.apply_search_filter(data, search, search_fields)
