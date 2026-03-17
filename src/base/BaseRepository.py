from typing import Optional, List, Dict, Any, Tuple
from src.config.Database import get_firestore_client
from google.cloud.firestore_v1 import FieldFilter
from datetime import datetime

class BaseRepository:
    """Base repository with generic CRUD operations"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.db = get_firestore_client()
        self.collection = self.db.collection(collection_name)
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document and return the created document"""
        doc_ref = self.collection.document()
        data['id'] = doc_ref.id
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        if 'is_active' not in data:
            data['is_active'] = True
        if 'is_deleted' not in data:
            data['is_deleted'] = False
        doc_ref.set(data)
        return data
    
    def get_by_id(self, doc_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get document by ID (excludes soft-deleted by default)"""
        doc = self.collection.document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            if not include_deleted and data.get('is_deleted', False):
                return None
            return data
        return None
    
    def get_by_field(self, field: str, value: Any, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get first document matching field value (excludes soft-deleted by default)"""
        query = self.collection.where(filter=FieldFilter(field, "==", value))
        
        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))
        
        docs = query.limit(1).get()
        if docs:
            return docs[0].to_dict()
        return None
    
    def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get document by email field (convenience method)"""
        return self.get_by_field("email", email, include_deleted)
    
    def get_all(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """Get all documents with optional filters (excludes soft-deleted by default)"""
        query = self.collection
        
        # Always filter out soft-deleted unless explicitly requested
        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))
        
        if filters:
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, "==", value))
        
        if limit:
            query = query.limit(limit)
        
        docs = query.get()
        return [doc.to_dict() for doc in docs]
    
    def get_paginated(
        self, 
        page: int = 1, 
        page_size: int = 10, 
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Get paginated documents
        Returns: (items, total_count, total_pages)
        """
        query = self.collection
        
        # Always filter out soft-deleted unless explicitly requested
        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))
        
        if filters:
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, "==", value))
        
        # Get total count
        all_docs = query.get()
        total_count = len(all_docs)
        total_pages = (total_count + page_size - 1) // page_size
        
        # Apply ordering
        if order_by:
            from google.cloud.firestore_v1 import Query
            direction = Query.DESCENDING if order_direction.lower() == "desc" else Query.ASCENDING
            query = query.order_by(order_by, direction=direction)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)
        
        docs = query.get()
        items = [doc.to_dict() for doc in docs]
        
        return items, total_count, total_pages
    
    def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update document by ID"""
        try:
            data['updated_at'] = datetime.utcnow()
            self.collection.document(doc_id).update(data)
            return True
        except Exception:
            return False
    
    def delete(self, doc_id: str) -> bool:
        """Hard delete document by ID (NOT RECOMMENDED - use soft_delete instead)"""
        try:
            self.collection.document(doc_id).delete()
            return True
        except Exception:
            return False
    
    def soft_delete(self, doc_id: str) -> bool:
        """Soft delete by setting is_deleted to True and is_active to False"""
        return self.update(doc_id, {
            'is_deleted': True,
            'is_active': False,
            'deleted_at': datetime.utcnow()
        })
    
    def restore(self, doc_id: str) -> bool:
        """Restore a soft-deleted document"""
        return self.update(doc_id, {
            'is_deleted': False,
            'is_active': True,
            'restored_at': datetime.utcnow()
        })
    
    def exists(self, field: str, value: Any, include_deleted: bool = False) -> bool:
        """Check if document exists with field value (excludes soft-deleted by default)"""
        query = self.collection.where(filter=FieldFilter(field, "==", value))
        
        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))
        
        docs = query.limit(1).get()
        return len(docs) > 0
    
    def count(self, filters: Optional[Dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """Count documents with optional filters (excludes soft-deleted by default)"""
        query = self.collection
        
        # Always filter out soft-deleted unless explicitly requested
        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))
        
        if filters:
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, "==", value))
        
        return len(query.get())
