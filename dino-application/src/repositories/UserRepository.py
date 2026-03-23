from src.base.BaseRepository import BaseRepository
from google.cloud import firestore
from typing import Dict, Any
from datetime import datetime, timezone
import random

class UserRepository(BaseRepository):
    """User repository for both system and application users"""
    
    def __init__(self, collection_name: str):
        """
        Initialize user repository
        Args:
            collection_name: Either 'system_users' or 'application_users'
        """
        super().__init__(collection_name)
    
    def generate_system_user_id(self) -> str:
        """
        Generate a unique 4-digit ID for system users using a Firestore
        transaction to atomically check-and-reserve the ID, eliminating
        any race condition between concurrent registrations.
        Returns a string like '1000', '1001', etc.
        """
        max_attempts = 100

        for _ in range(max_attempts):
            candidate_id = str(random.randint(1000, 9999))
            doc_ref = self.collection.document(candidate_id)

            @firestore.transactional
            def _try_reserve(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                if snapshot.exists:
                    return None
                # Reserve the slot with a sentinel so no other transaction
                # can claim the same ID concurrently.
                transaction.set(ref, {'_reserved': True})
                return ref.id

            transaction = self.db.transaction()
            reserved_id = _try_reserve(transaction, doc_ref)
            if reserved_id is not None:
                return reserved_id

        raise Exception("Unable to generate unique 4-digit user ID. All IDs may be taken.")
    
    def create_system_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new system user with a 4-digit ID.
        generate_system_user_id() atomically reserves the document slot;
        this method then writes the full user payload over it.
        """
        # Atomically reserve a unique 4-digit ID
        user_id = self.generate_system_user_id()
        
        now = datetime.now(timezone.utc)

        doc_ref = self.collection.document(user_id)
        data['id'] = user_id
        data['created_at'] = now.isoformat()
        data['updated_at'] = now.isoformat()
        if 'is_active' not in data:
            data['is_active'] = True
        if 'is_deleted' not in data:
            data['is_deleted'] = False
        
        # Overwrite the reservation sentinel with the real user document
        doc_ref.set(data)
        return data