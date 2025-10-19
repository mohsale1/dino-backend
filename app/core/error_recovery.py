"""
Error Recovery Utilities
Provides utilities for graceful error handling and recovery
"""
from typing import Any, Dict, List, Optional, Callable
from fastapi import HTTPException, status
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def safe_execute(func: Callable, *args, default_return=None, log_errors=True, **kwargs):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        default_return: Value to return if function fails
        log_errors: Whether to log errors
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or default_return if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default_return


async def safe_execute_async(func: Callable, *args, default_return=None, log_errors=True, **kwargs):
    """
    Safely execute an async function with error handling
    
    Args:
        func: Async function to execute
        *args: Arguments for the function
        default_return: Value to return if function fails
        log_errors: Whether to log errors
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or default_return if error occurs
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default_return


# Import from common utils to avoid duplication
from app.core.common_utils import validate_required_fields, raise_validation_error


def handle_firestore_operator_error(error: Exception) -> Exception:
    """
    Handle Firestore operator errors and provide helpful messages
    
    Args:
        error: Original exception
    
    Returns:
        Modified exception with helpful message
    """
    error_msg = str(error).lower()
    
    if "operator string" in error_msg and "invalid" in error_msg:
        # Extract operator information if possible
        if "array-contains-any" in error_msg:
            return Exception("Invalid Firestore operator: Use 'array_contains_any' instead of 'array-contains-any'")
        elif "array-contains" in error_msg:
            return Exception("Invalid Firestore operator: Use 'array_contains' instead of 'array-contains'")
        else:
            return Exception(f"Invalid Firestore operator. Check your query filters. Original error: {error}")
    
    return error


class ErrorRecoveryMixin:
    """
    Mixin class to add error recovery capabilities to endpoints
    """
    
    async def safe_get_items(self, repo, filters=None, default_return=None):
        """
        Safely get items from repository with error recovery
        """
        try:
            if filters:
                return await repo.query(filters)
            else:
                return await repo.get_all()
        except Exception as e:
            logger.error(f"Error getting items from {repo.collection_name}: {e}")
            return default_return or []
    
    async def safe_get_by_id(self, repo, item_id, default_return=None):
        """
        Safely get item by ID with error recovery
        """
        try:
            return await repo.get_by_id(item_id)
        except Exception as e:
            logger.error(f"Error getting item {item_id} from {repo.collection_name}: {e}")
            return default_return
    
    def safe_create_dto(self, dto_class, data, log_prefix=""):
        """
        Safely create DTO object with error recovery
        """
        try:
            return dto_class(**data)
        except Exception as e:
            logger.error(f"{log_prefix}Error creating DTO {dto_class.__name__}: {e}")
            logger.error(f"{log_prefix}Data: {data}")
            return None