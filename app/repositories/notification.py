"""
Notification Repository
"""
from typing import List, Dict, Any
from datetime import datetime
from app.repositories.base import BaseRepository

class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__("notifications")
    
    async def get_by_recipient(self, recipient_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        filters = [('recipient_id', '==', recipient_id)]
        if unread_only:
            filters.append(('is_read', '==', False))
        return await self.query(filters)
    
    async def mark_as_read(self, notification_id: str) -> bool:
        await self.update(notification_id, {'is_read': True, 'read_at': datetime.utcnow()})
        return True

def get_notification_repository() -> NotificationRepository:
    if '_notification_repo' not in globals():
        globals()['_notification_repo'] = NotificationRepository()
    return globals()['_notification_repo']