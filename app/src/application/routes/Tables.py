from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Table import TableCreate, TableUpdate, TableResponse
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.config.Database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import qrcode
import io
import base64

router = APIRouter(prefix="/tables", tags=["Application Tables"])


# ==================== BULK REQUEST MODELS ====================

class BulkUpdateTableStatusRequest(BaseModel):
    table_ids: List[int]
    table_status: str


# ==================== COLLECTION ENDPOINTS ====================

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:create'))])
async def create_table(
    table: TableCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new table (Admin only)"""
    service = TableService(db)

    table_id = await service.create_table(table.model_dump())

    return {
        "success": True,
        "message": "Table created successfully",
        "data": {"id": table_id}
    }

@router.get("", dependencies=[Depends(ApplicationPermissionCheck.require('tables:read'))])
async def get_all_tables(
    workspace_id: int = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    area_id: Optional[int] = Query(None, description="Filter by area"),
    status: Optional[str] = Query(None, description="Filter by status (available, occupied, reserved, maintenance)"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    db: AsyncSession = Depends(get_db)
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
    service = TableService(db)

    items, total, total_pages = await service.get_paginated_tables(
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


# ==================== STATIC-PATH ENDPOINTS (must be BEFORE /{table_id}) ====================

# /statistics must be registered BEFORE /{table_id} to avoid route shadowing
@router.get("/statistics", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:read'))])
async def get_table_statistics(
    workspace_id: int = Query(..., description="Workspace ID"),
    area_id: Optional[int] = Query(None, description="Filter by area"),
    db: AsyncSession = Depends(get_db)
):
    """Get table statistics"""
    from src.repositories.TableRepository import TableRepository

    table_repo = TableRepository(db)

    filters = {
        "workspace_id": workspace_id,
        "is_active": True
    }

    if area_id:
        filters["area_id"] = area_id

    tables = await table_repo.get_all(filters=filters)

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

@router.post("/bulk-update-status", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:update'))])
async def bulk_update_table_status(
    body: BulkUpdateTableStatusRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update table status (Admin, Manager)"""
    service = TableService(db)

    valid_statuses = ['available', 'occupied', 'reserved', 'maintenance']
    if body.table_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    updated_count = 0
    failed_tables = []

    for table_id in body.table_ids:
        try:
            table = await service.get_table_by_id(table_id)
            if not table:
                failed_tables.append({"id": table_id, "reason": "Table not found"})
                continue

            success = await service.update_table(table_id, {"status": body.table_status})
            if success:
                updated_count += 1
            else:
                failed_tables.append({"id": table_id, "reason": "Update failed"})
        except Exception as e:
            failed_tables.append({"id": table_id, "reason": str(e)})

    return {
        "success": True,
        "message": f"Updated {updated_count} tables to status: {body.table_status}",
        "data": {
            "updated_count": updated_count,
            "failed_tables": failed_tables
        }
    }


# ==================== TABLE-SCOPED ENDPOINTS (/{table_id}) ====================

@router.get("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:read'))])
async def get_table(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get table by ID"""
    service = TableService(db)

    table = await service.get_table_by_id(table_id)

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

@router.put("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:update'))])
async def update_table(
    table_id: int,
    table: TableUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update table (Admin only)"""
    service = TableService(db)

    existing_table = await service.get_table_by_id(table_id)
    if not existing_table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    success = await service.update_table(table_id, table.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    return {
        "success": True,
        "message": "Table updated successfully"
    }

@router.delete("/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:delete'))])
async def delete_table(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete table (Admin only)"""
    service = TableService(db)

    table = await service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    success = await service.soft_delete_table(table_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    return {
        "success": True,
        "message": "Table soft deleted successfully"
    }

@router.put("/{table_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:restore'))])
async def restore_table(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Restore soft-deleted table (Admin only)"""
    service = TableService(db)

    table = await service.get_table_by_id(table_id, include_deleted=True)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    if table.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Table is not deleted"
        )

    success = await service.restore_table(table_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    return {
        "success": True,
        "message": "Table restored successfully"
    }

@router.post("/{table_id}/qr-code", response_model=BaseResponse)
async def generate_qr_code(
    table_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:read')),
    db: AsyncSession = Depends(get_db)
):
    """Generate QR code for a table (returns base64 PNG data URL)"""
    from src.config.Settings import settings

    service = TableService(db)

    table = await service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    # Build the public menu URL that the QR code points to
    persona_id = table.get('persona_id', '')
    workspace_id = table.get('workspace_id', '')

    # Construct the public menu URL
    base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    qr_url = f"{base_url}/{persona_id}/{table_id}/menu"

    # Generate QR code image (sync — qrcode library is synchronous)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    b64 = base64.b64encode(buffer.read()).decode("utf-8")
    qr_code_url = f"data:image/png;base64,{b64}"

    # Persist the QR code URL on the table record
    await service.update_table(table_id, {"qr_code_url": qr_code_url, "qr_menu_url": qr_url})

    return {
        "success": True,
        "message": "QR code generated successfully",
        "data": {
            "qr_code_url": qr_code_url,
            "qr_menu_url": qr_url,
            "table_id": table_id,
            "table_number": table.get('table_number')
        }
    }


@router.get("/{table_id}/qr-code/print", dependencies=[Depends(ApplicationPermissionCheck.require('tables:read'))])
async def print_qr_code(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get printable QR code PNG for a table"""
    from fastapi.responses import Response

    service = TableService(db)

    table = await service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    qr_code_url = table.get('qr_code_url', '')
    if not qr_code_url or not qr_code_url.startswith('data:image/png;base64,'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not generated yet. Call POST /tables/{table_id}/qr-code first."
        )

    # Decode base64 back to PNG bytes
    b64_data = qr_code_url.split(',', 1)[1]
    png_bytes = base64.b64decode(b64_data)

    table_number = table.get('table_number', table_id)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="table-{table_number}-qr.png"'}
    )


@router.put("/{table_id}/status", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('tables:update'))])
async def update_table_status(
    table_id: int,
    table_status: str = Query(..., description="Table status (available, occupied, reserved, maintenance)"),
    db: AsyncSession = Depends(get_db)
):
    """Update table status (Admin, Manager, Operator)"""
    service = TableService(db)

    valid_statuses = ['available', 'occupied', 'reserved', 'maintenance']
    if table_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    table = await service.get_table_by_id(table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    success = await service.update_table(table_id, {"status": table_status})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    return {
        "success": True,
        "message": f"Table status updated to {table_status}"
    }
