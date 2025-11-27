"""
Table Service
Business logic for table management
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.entities import TableStatus
from app.database.repository_manager import get_table_repo
from app.utils.qr_code import generate_qr_code, generate_qr_code_url
from app.core.logging import get_logger

logger = get_logger(__name__)


class TableService:
    """Service for table business logic"""
    
    def __init__(self):
        self.repo = get_table_repo()
    
    async def generate_table_qr_code(self, venue_id: str, table_number: int) -> Dict[str, str]:
        """Generate QR code for a table"""
        qr_code = generate_qr_code(venue_id, table_number)
        qr_code_url = generate_qr_code_url(qr_code)
        
        return {
            "qr_code": qr_code,
            "qr_code_url": qr_code_url
        }
    
    async def regenerate_table_qr_code(self, table_id: str, venue_id: str, table_number: int) -> Dict[str, str]:
        """Regenerate QR code for a table"""
        # Generate new QR code with timestamp for uniqueness
        salt = datetime.utcnow().isoformat()
        qr_code = generate_qr_code(venue_id, table_number, salt)
        qr_code_url = generate_qr_code_url(qr_code)
        
        # Update table with new QR code
        await self.repo.update(table_id, {
            "qr_code": qr_code,
            "qr_code_url": qr_code_url,
            "qr_regenerated_at": datetime.utcnow()
        })
        
        logger.info(f"Regenerated QR code for table {table_id}")
        
        return {
            "qr_code": qr_code,
            "qr_code_url": qr_code_url
        }
    
    async def update_table_status(self, table_id: str, status: TableStatus, user_id: str) -> bool:
        """Update table status"""
        await self.repo.update(table_id, {
            "status": status.value,
            "status_updated_at": datetime.utcnow(),
            "status_updated_by": user_id
        })
        
        logger.info(f"Table {table_id} status updated to {status.value} by user {user_id}")
        return True
    
    async def get_table_statistics(self, venue_id: str) -> Dict[str, Any]:
        """Get table statistics for a venue"""
        tables = await self.repo.get_by_venue(venue_id)
        
        total_tables = len(tables)
        available_tables = len([t for t in tables if t.get('status') == TableStatus.AVAILABLE.value])
        occupied_tables = len([t for t in tables if t.get('status') == TableStatus.OCCUPIED.value])
        reserved_tables = len([t for t in tables if t.get('status') == TableStatus.RESERVED.value])
        
        # Group by area
        tables_by_area = {}
        for table in tables:
            area_id = table.get('area_id', 'unassigned')
            if area_id not in tables_by_area:
                tables_by_area[area_id] = []
            tables_by_area[area_id].append(table)
        
        return {
            "venue_id": venue_id,
            "total_tables": total_tables,
            "available_tables": available_tables,
            "occupied_tables": occupied_tables,
            "reserved_tables": reserved_tables,
            "tables_by_area": {
                area_id: len(tables_list) 
                for area_id, tables_list in tables_by_area.items()
            }
        }
    
    async def verify_qr_code(self, qr_code: str) -> Optional[Dict[str, Any]]:
        """Verify QR code and return table information"""
        tables = await self.repo.query([('qr_code', '==', qr_code)])
        
        if not tables:
            return None
        
        table = tables[0]
        
        # Get venue information
        from app.database.repository_manager import get_venue_repo
        venue_repo = get_venue_repo()
        venue = await venue_repo.get_by_id(table.get('venue_id'))
        
        return {
            "table": table,
            "venue": venue,
            "is_valid": True,
            "verified_at": datetime.utcnow()
        }
    
    async def bulk_update_table_status(self, table_ids: List[str], status: TableStatus, user_id: str) -> int:
        """Bulk update table status"""
        updated_count = 0
        
        for table_id in table_ids:
            try:
                await self.update_table_status(table_id, status, user_id)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating table {table_id}: {e}")
        
        logger.info(f"Bulk updated {updated_count}/{len(table_ids)} tables to status {status.value}")
        return updated_count


# Singleton instance
_table_service = None

def get_table_service() -> TableService:
    """Get table service singleton"""
    global _table_service
    if _table_service is None:
        _table_service = TableService()
    return _table_service