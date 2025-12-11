"""
Base Repository
Provides common CRUD operations for all repositories
"""
from typing import List, Dict, Any, Optional, TypeVar, Generic
from datetime import datetime
from abc import ABC, abstractmethod

from app.database.firestore import get_firestore_client
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, collection_name: str):
        self.db = get_firestore_client()
        self.collection_name = collection_name
        self.collection = self.db.collection(collection_name)
    
    async def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document"""
        try:
            # Add timestamps using centralized utility
            from app.core.utils import add_timestamps
            from app.utils.id_generator import generate_document_id
            data = add_timestamps(data, is_update=False)
            
            if doc_id:
                # Use specific document ID
                doc_ref = self.collection.document(doc_id)
                data['id'] = doc_id
            else:
                # Auto-generate UUID
                generated_id = generate_document_id()
                doc_ref = self.collection.document(generated_id)
                data['id'] = generated_id
            
            doc_ref.set(data)
            logger.info(f"Created document in {self.collection_name}: {data['id']}")
            return data
            
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise
    
    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            doc = self.collection.document(doc_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting document {doc_id} from {self.collection_name}: {e}")
            raise
    
    async def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all documents"""
        try:
            query = self.collection
            if limit:
                query = query.limit(limit)
            
            docs = list(query.stream())
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error getting all documents from {self.collection_name}: {e}")
            raise
    
    async def update(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document with proper nested object merging"""
        try:
            # Add updated timestamp using centralized utility
            from app.core.utils import add_timestamps
            data = add_timestamps(data, is_update=True)
            
            doc_ref = self.collection.document(doc_id)
            
            # Get existing document to merge nested objects
            existing_doc = await self.get_by_id(doc_id)
            if not existing_doc:
                raise ValueError(f"Document {doc_id} not found")
            
            # Merge nested objects (like location) instead of replacing them
            merged_data = {}
            for key, value in data.items():
                if isinstance(value, dict) and key in existing_doc and isinstance(existing_doc[key], dict):
                    # Merge nested dictionaries
                    merged_data[key] = {**existing_doc[key], **value}
                else:
                    merged_data[key] = value
            
            doc_ref.update(merged_data)
            
            logger.info(f"Updated document in {self.collection_name}: {doc_id}")
            
            # Return updated document
            updated_doc = await self.get_by_id(doc_id)
            return updated_doc
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id} in {self.collection_name}: {e}")
            raise
    
    async def delete(self, doc_id: str) -> bool:
        """Delete document"""
        try:
            self.collection.document(doc_id).delete()
            logger.info(f"Deleted document from {self.collection_name}: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} from {self.collection_name}: {e}")
            raise
    
    async def query(self, filters: List[tuple], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query documents with filters
        
        Args:
            filters: List of tuples (field, operator, value)
            limit: Maximum number of results
            
        Example:
            filters = [('venue_id', '==', 'venue123'), ('is_active', '==', True)]
        """
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            query = self.collection
            
            for field, operator, value in filters:
                # Use the new filter() method with FieldFilter to avoid deprecation warning
                query = query.where(filter=FieldFilter(field, operator, value))
            
            if limit:
                query = query.limit(limit)
            
            docs = list(query.stream())
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            logger.error(f"Error querying {self.collection_name}: {e}", exc_info=True)
            logger.error(f"Query filters: {filters}")
            raise
    
    async def exists(self, doc_id: str) -> bool:
        """Check if document exists"""
        try:
            doc = self.collection.document(doc_id).get()
            return doc.exists
        except Exception as e:
            logger.error(f"Error checking existence of {doc_id} in {self.collection_name}: {e}")
            raise
    
    async def count(self, filters: Optional[List[tuple]] = None) -> int:
        """Count documents"""
        try:
            if filters:
                docs = await self.query(filters)
                return len(docs)
            else:
                docs = await self.get_all()
                return len(docs)
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            raise
    
    async def batch_create(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple documents in batch"""
        try:
            created_items = []
            batch = self.db.batch()
            
            from app.core.utils import add_timestamps
            from app.utils.id_generator import generate_document_id
            for item in items:
                generated_id = generate_document_id()
                doc_ref = self.collection.document(generated_id)
                item['id'] = generated_id
                item = add_timestamps(item, is_update=False)
                
                batch.set(doc_ref, item)
                created_items.append(item)
            
            batch.commit()
            logger.info(f"Batch created {len(created_items)} documents in {self.collection_name}")
            return created_items
            
        except Exception as e:
            logger.error(f"Error batch creating documents in {self.collection_name}: {e}")
            raise
    
    async def batch_update(self, updates: List[tuple]) -> bool:
        """
        Update multiple documents in batch
        
        Args:
            updates: List of tuples (doc_id, update_data)
        """
        try:
            batch = self.db.batch()
            
            from app.core.utils import add_timestamps
            for doc_id, update_data in updates:
                doc_ref = self.collection.document(doc_id)
                update_data = add_timestamps(update_data, is_update=True)
                batch.update(doc_ref, update_data)
            
            batch.commit()
            logger.info(f"Batch updated {len(updates)} documents in {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error batch updating documents in {self.collection_name}: {e}")
            raise
    
    async def batch_delete(self, doc_ids: List[str]) -> bool:
        """Delete multiple documents in batch"""
        try:
            batch = self.db.batch()
            
            for doc_id in doc_ids:
                doc_ref = self.collection.document(doc_id)
                batch.delete(doc_ref)
            
            batch.commit()
            logger.info(f"Batch deleted {len(doc_ids)} documents from {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error batch deleting documents from {self.collection_name}: {e}")
            raise
    
    async def get_by_ids_batch(self, ids: List[str], fields: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch multiple documents by IDs in a single query (optimized for N+1 problem)
        
        Args:
            ids: List of document IDs to fetch
            fields: Optional list of fields to return (field projection)
        
        Returns:
            Dictionary mapping document ID to document data
        
        Note:
            Firestore 'in' query supports up to 10 items per query.
            This method automatically batches larger requests.
        """
        if not ids:
            return {}
        
        try:
            all_docs = {}
            batch_size = 10  # Firestore limit for 'in' queries
            
            # Split into batches of 10
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                
                # Query documents by ID
                query = self.collection.where('__name__', 'in', [
                    self.collection.document(doc_id) for doc_id in batch_ids
                ])
                
                # Apply field projection if specified
                if fields:
                    query = query.select(fields)
                
                docs = list(query.stream())
                for doc in docs:
                    all_docs[doc.id] = doc.to_dict()
            
            logger.debug(f"Batch fetched {len(all_docs)} documents from {self.collection_name}")
            return all_docs
            
        except Exception as e:
            logger.error(f"Error batch fetching documents from {self.collection_name}: {e}")
            raise
    
    async def get_with_fields(self, doc_id: str, fields: List[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch document with only specified fields (field projection)
        
        Args:
            doc_id: Document ID
            fields: List of field names to return
        
        Returns:
            Dictionary with only requested fields
        
        Example:
            user = await repo.get_with_fields('user123', ['id', 'email', 'first_name'])
        """
        try:
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get(field_paths=fields)
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id} with fields from {self.collection_name}: {e}")
            raise
    
    async def query_with_fields(
        self, 
        filters: List[tuple], 
        fields: List[str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query documents with field projection
        
        Args:
            filters: List of tuples (field, operator, value)
            fields: List of field names to return
            limit: Maximum number of results
        
        Returns:
            List of documents with only requested fields
        """
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            query = self.collection
            
            # Apply filters
            for field, operator, value in filters:
                query = query.where(filter=FieldFilter(field, operator, value))
            
            # Apply field projection
            query = query.select(fields)
            
            if limit:
                query = query.limit(limit)
            
            docs = list(query.stream())
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            logger.error(f"Error querying {self.collection_name} with fields: {e}")
            raise