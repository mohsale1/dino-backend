from datetime import datetime
from typing import Any, Dict, Optional

def format_datetime(dt: datetime) -> Optional[str]:
    """Format datetime to ISO string"""
    return dt.isoformat() if dt else None

def sanitize_dict(data: Dict[str, Any], exclude_keys: list = None) -> Dict[str, Any]:
    """Remove None values and specified keys from dictionary"""
    if exclude_keys is None:
        exclude_keys = []
    
    return {
        k: v for k, v in data.items()
        if v is not None and k not in exclude_keys
    }

def paginate_list(items: list, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """Paginate a list of items"""
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }