from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Table import TableCreate, TableUpdate, TableResponse
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Optional, List

router = APIRouter(prefix="/tables", tags=["Application Tables"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_table(table: TableCreate):
    """Create new table (Admin only)"""
    service = TableService()
    
    table_id = service.create_table(table.model_dump())
    
    return {
        "success": True,
        "message": "Table created successfully",
        "data": {"id": table_id}
    }

@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_all_tables(
    workspace_id: str = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    area_id: Optional[str] = Query(None, description="Filter by area"),
    status: Optional[str] = Query(None, description="Filter by status (available, occupied, reserved, maintenance)"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)")
):
    """
    Get all tables with pagination and filters
    
    Query Parameters:
    - workspace_id: Workspace ID (required)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - area_id: Filter by area
    - status: Filter by status (available, occupied, reserved, maintenance)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = TableService()
    
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated_tables(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        area_id=area_id,
        status=status,
        order_by=order_by,
        order_direction=order_direction
    )
    
    return {
        "success": True,
        "message": "Tables retrieved successfully",
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

@router.get("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_table(table_id: str):
    """Get table by ID"""
    service = TableService()
    
    table = service.get_table_by_id(table_id)
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table retrieved successfully",
        "data": table
    }

@router.put("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_table(table_id: str, table: TableUpdate):
    """Update table (Admin only)"""
    service = TableService()
    
    # Check if table exists
    existing_table = service.get_table_by_id(table_id)
    if not existing_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    success = service.update_table(table_id, table.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table updated successfully"
    }

@router.delete("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_table(table_id: str):
    """Soft delete table (Admin only)"""
    service = TableService()
    
    # Check if table exists
    table = service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    success = service.soft_delete_table(table_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table soft deleted successfully"
    }

@router.put("/{table_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_table(table_id: str):
    """Restore soft-deleted table (Admin only)"""
    service = TableService()
    
    # Check if table exists (including deleted)
    table = service.get_table_by_id(table_id, include_deleted=True)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    if not table.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Table is not deleted"
        )
    
    success = service.restore_table(table_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table restored successfully"
    }

@router.put("/{table_id}/status", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def update_table_status(
    table_id: str,
    status: str = Query(..., description="Table status (available, occupied, reserved, maintenance)")
):
    """Update table status (Admin, Manager, Operator)"""
    service = TableService()
    
    # Validate status
    valid_statuses = ['available', 'occupied', 'reserved', 'maintenance']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Check if table exists
    table = service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    success = service.update_table(table_id, {"status": status})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": f"Table status updated to {status}"
    }

@router.post("/bulk-update-status", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def bulk_update_table_status(
    table_ids: List[str],
    status: str
):
    """Bulk update table status (Admin, Manager)"""
    service = TableService()
    
    # Validate status
    valid_statuses = ['available', 'occupied', 'reserved', 'maintenance']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    updated_count = 0
    failed_tables = []
    
    for table_id in table_ids:
        try:
            table = service.get_table_by_id(table_id)
            if not table:
                failed_tables.append({"id": table_id, "reason": "Table not found"})
                continue
            
            success = service.update_table(table_id, {"status": status})
            if success:
                updated_count += 1
            else:
                failed_tables.append({"id": table_id, "reason": "Update failed"})
        except Exception as e:
            failed_tables.append({"id": table_id, "reason": str(e)})
    
    return {
        "success": True,
        "message": f"Updated {updated_count} tables to status: {status}",
        "data": {
            "updated_count": updated_count,
            "failed_tables": failed_tables
        }
    }

@router.get("/statistics", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_table_statistics(
    workspace_id: str = Query(..., description="Workspace ID"),
    area_id: Optional[str] = Query(None, description="Filter by area")
):
    """Get table statistics"""
    from src.repositories.TableRepository import TableRepository
    
    table_repo = TableRepository()
    
    # Build filters
    filters = {
        "workspace_id": workspace_id,
        "is_deleted": False
    }
    
    if area_id:
        filters["area_id"] = area_id
    
    # Get all tables
    tables = table_repo.get_all(filters=filters)
    
    # Calculate statistics
    total_tables = len(tables)
    available_tables = len([t for t in tables if t.get('status') == 'available'])
    occupied_tables = len([t for t in tables if t.get('status') == 'occupied'])
    reserved_tables = len([t for t in tables if t.get('status') == 'reserved'])
    maintenance_tables = len([t for t in tables if t.get('status') == 'maintenance'])
    total_capacity = sum(t.get('capacity', 0) for t in tables)
    
    return {
        "success": True,
        "message": "Table statistics retrieved successfully",
        "data": {
            "total_tables": total_tables,
            "available_tables": available_tables,
            "occupied_tables": occupied_tables,
            "reserved_tables": reserved_tables,
            "maintenance_tables": maintenance_tables,
            "total_capacity": total_capacity,
            "occupancy_rate": round((occupied_tables / total_tables * 100) if total_tables > 0 else 0, 2)
        }
    }