"""
Unified Response Builder
Centralized response creation for consistent API responses across the application
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel


class ResponseBuilder:
    """Centralized response builder for all API responses"""
    
    @staticmethod
    def success(
        message: str,
        data: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create standardized success response
        
        Args:
            message: Success message
            data: Optional data to include
            **kwargs: Additional fields to include in response
            
        Returns:
            Standardized success response dictionary
        """
        response = {
            "success": True,
            "message": message
        }
        
        if data is not None:
            response["data"] = data
        
        # Add any additional fields
        response.update(kwargs)
        
        return response
    
    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        details: Any = None,
        status_code: int = 500
    ) -> Dict[str, Any]:
        """
        Create standardized error response
        
        Args:
            message: Error message
            error_code: Optional error code
            details: Optional error details
            status_code: HTTP status code
            
        Returns:
            Standardized error response dictionary
        """
        response = {
            "success": False,
            "error": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create standardized paginated response
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page
            **kwargs: Additional fields
            
        Returns:
            Standardized paginated response
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        response = {
            "success": True,
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
        # Add any additional fields
        response.update(kwargs)
        
        return response
    
    @staticmethod
    def created(
        message: str,
        data: Any,
        resource_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized creation response
        
        Args:
            message: Success message
            data: Created resource data
            resource_id: Optional resource ID
            
        Returns:
            Standardized creation response
        """
        response = {
            "success": True,
            "message": message,
            "data": data
        }
        
        if resource_id:
            response["resource_id"] = resource_id
        
        return response
    
    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> Dict[str, Any]:
        """
        Create standardized deletion response
        
        Args:
            message: Success message
            
        Returns:
            Standardized deletion response
        """
        return {
            "success": True,
            "message": message
        }
    
    @staticmethod
    def updated(
        message: str = "Resource updated successfully",
        data: Any = None
    ) -> Dict[str, Any]:
        """
        Create standardized update response
        
        Args:
            message: Success message
            data: Optional updated resource data
            
        Returns:
            Standardized update response
        """
        response = {
            "success": True,
            "message": message
        }
        
        if data is not None:
            response["data"] = data
        
        return response


# Global instance
response_builder = ResponseBuilder()


# Convenience functions for backward compatibility
def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """Create success response - backward compatible"""
    return response_builder.success(message, data)


def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    details: Any = None
) -> Dict[str, Any]:
    """Create error response - backward compatible"""
    return response_builder.error(message, error_code, details)


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """Create paginated response - backward compatible"""
    return response_builder.paginated(items, total, page, page_size)