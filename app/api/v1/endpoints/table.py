"""

Enhanced Table Management API Endpoints

Complete CRUD for tables with QR code generation and status management

"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query

from datetime import datetime, timezone

import hashlib

import base64

import json



from app.models.schemas import Table, TableStatus

from app.models.dto import (

  TableCreateDTO, TableUpdateDTO, TableResponseDTO, QRCodeDataDTO,

  ApiResponseDTO, PaginatedResponseDTO

)

from pydantic import BaseModel

# Removed base endpoint dependency

from app.core.base_endpoint import WorkspaceIsolatedEndpoint

from app.database.firestore import get_table_repo, TableRepository

from app.core.security import get_current_user, get_current_admin_user

from app.core.logging_config import get_logger



logger = get_logger(__name__)

router = APIRouter()





class TablesEndpoint(WorkspaceIsolatedEndpoint[Table, TableCreateDTO, TableUpdateDTO]):

  """Enhanced Tables endpoint with QR code management and status tracking"""

   

  def __init__(self):

    super().__init__(

      model_class=Table,

      create_schema=TableCreateDTO,

      update_schema=TableUpdateDTO,

      collection_name="tables",

      require_auth=True,

      require_admin=True

    )

   

  def get_repository(self) -> TableRepository:

    return get_table_repo()

   

  async def _prepare_create_data(self, 

                 data: Dict[str, Any], 

                 current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:

    """Prepare table data before creation"""

    # Generate QR code

    venue_id = data['venue_id']

    table_number = data['table_number']

    qr_code = self._generate_qr_code(venue_id, table_number)

     

    data['qr_code'] = qr_code

    data['qr_code_url'] = None # Will be set when QR image is generated

    data['table_status'] = TableStatus.AVAILABLE.value

    data['is_active'] = True

     

    return data

   

  def _generate_qr_code(self, venue_id: str, table_number: int) -> str:

    """Generate encrypted QR code for table"""

    # Create QR data

    qr_data = {

      "venue_id": venue_id,

      "table_number": table_number,

      "type": "table_access"

    }

     

    # Convert to JSON and encode

    qr_json = json.dumps(qr_data, sort_keys=True)

    qr_bytes = qr_json.encode('utf-8')

     

    # Create hash for verification

    hash_object = hashlib.sha256(qr_bytes)

    qr_hash = hash_object.hexdigest()[:16] # Use first 16 chars

     

    # Encode with base64

    qr_encoded = base64.b64encode(qr_bytes).decode('utf-8')

     

    # Combine encoded data with hash

    return f"{qr_encoded}.{qr_hash}"

   

  def _verify_qr_code(self, qr_code: str) -> Optional[QRCodeDataDTO]:

    """Verify and decode QR code"""

    try:

      # Split encoded data and hash

      parts = qr_code.split('.')

      if len(parts) != 2:

        return None

       

      qr_encoded, qr_hash = parts

       

      # Decode data

      qr_bytes = base64.b64decode(qr_encoded.encode('utf-8'))

       

      # Verify hash

      hash_object = hashlib.sha256(qr_bytes)

      expected_hash = hash_object.hexdigest()[:16]

       

      if qr_hash != expected_hash:

        return None

       

      # Parse JSON

      qr_json = qr_bytes.decode('utf-8')

      qr_data = json.loads(qr_json)

       

      return QRCodeDataDTO(

        venue_id=qr_data['venue_id'],

        table_id=qr_data.get('table_id', ''),

        table_number=qr_data['table_number'],

        encrypted_token=qr_code,

        generated_at=datetime.now(timezone.utc)

      )

       

    except Exception:

      return None

   

  async def _validate_create_permissions(self, 

                     data: Dict[str, Any], 

                     current_user: Optional[Dict[str, Any]]):

    """Validate table creation permissions"""

    if not current_user:

      raise HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Authentication required"

      )

     

    # Validate venue access

    venue_id = data.get('venue_id')

    if venue_id:

      await self._validate_venue_access(venue_id, current_user)

     

    # Check for duplicate table number in venue

    table_number = data.get('table_number')

    if venue_id and table_number:

      repo = self.get_repository()

      existing_table = await repo.get_by_table_number(venue_id, table_number)

      if existing_table:

        raise HTTPException(

          status_code=status.HTTP_400_BAD_REQUEST,

          detail=f"Table number {table_number} already exists in this venue"

        )

   

  async def _validate_access_permissions(self, 

                     item: Dict[str, Any], 

                     current_user: Optional[Dict[str, Any]]):

    """Override to allow public access for table information"""

    # Allow public access for table information (QR code scanning)

    if current_user is None:

      return

     

    # For authenticated users, use normal workspace validation

    await super()._validate_access_permissions(item, current_user)

   

  async def _validate_venue_access(self, venue_id: str, current_user: Dict[str, Any]):

    """Validate user has access to the venue"""

    from app.database.firestore import get_venue_repo

    from app.core.security import _get_user_role

     

    venue_repo = get_venue_repo()

     

    venue = await venue_repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Get the actual role name from role_id

    user_role = await _get_user_role(current_user)

     

    # SuperAdmin and Admin have access to all venues

    if user_role in ['superadmin', 'admin']:

      return

     

    # For other roles, check workspace access

    user_workspace_id = current_user.get('workspace_id')

    venue_workspace_id = venue.get('workspace_id')

     

    if user_workspace_id != venue_workspace_id:

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Access denied: Venue belongs to different workspace"

      )

   

  async def get_table_by_qr_code(self, qr_code: str) -> Optional[Table]:

    """Get table by QR code"""

    repo = self.get_repository()

    table_data = await repo.get_by_qr_code(qr_code)

     

    if table_data:

      return Table(**table_data)

    return None

   

  async def update_table_status(self, 

                table_id: str,

                new_status: TableStatus,

                current_user: Dict[str, Any]) -> bool:

    """Update table status"""

    repo = self.get_repository()

     

    # Validate table exists and user has access

    table_data = await repo.get_by_id(table_id)

    if not table_data:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Table not found"

      )

     

    await self._validate_access_permissions(table_data, current_user)

     

    # Update status

    await repo.update(table_id, {"table_status": new_status.value})

     

    logger.info(f"Table status updated: {table_id} -> {new_status.value}")

    return True

   

  async def get_venue_table_statistics(self, 

                   venue_id: str,

                   current_user: Dict[str, Any]) -> Dict[str, Any]:

    """Get table statistics for a venue"""

    # Validate venue access

    await self._validate_venue_access(venue_id, current_user)

     

    repo = self.get_repository()

    tables = await repo.get_by_venue(venue_id)

     

    # Count by status

    status_counts = {}

    for status in TableStatus:

      status_counts[status.value] = 0

     

    active_tables = 0

    for table in tables:

      if table.get('is_active', False):

        active_tables += 1

        table_status = table.get('table_status', TableStatus.AVAILABLE.value)

        status_counts[table_status] += 1

     

    return {

      "venue_id": venue_id,

      "total_tables": len(tables),

      "active_tables": active_tables,

      "status_breakdown": status_counts,

      "utilization_rate": (status_counts.get('occupied', 0) / active_tables * 100) if active_tables > 0 else 0

    }





# Initialize endpoint

tables_endpoint = TablesEndpoint()





# =============================================================================

# TABLE MANAGEMENT ENDPOINTS

# =============================================================================



@router.get("", 

      response_model=PaginatedResponseDTO,

      summary="Get tables",

      description="Get paginated list of tables")

async def get_tables(

  page: int = Query(1, ge=1, description="Page number"),

  page_size: int = Query(10, ge=1, le=100, description="Items per page"),

  venue_id: Optional[str] = Query(None, description="Filter by venue ID"),

  table_status: Optional[TableStatus] = Query(None, description="Filter by table status"),

  is_active: Optional[bool] = Query(None, description="Filter by active status"),

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get tables with pagination and filtering"""

  filters = {}

  if venue_id:

    filters['venue_id'] = venue_id

  if table_status:

    filters['table_status'] = table_status.value

  if is_active is not None:

    filters['is_active'] = is_active

   

  try:

    result = await tables_endpoint.get_items(

      page=page,

      page_size=page_size,

      filters=filters,

      current_user=current_user

    )

    return result

  except Exception as e:

    logger.error(f"Error getting tables list: {e}")

    # If it's a validation error, try to fix the data

    if "validation error" in str(e).lower() and "table_status" in str(e).lower():

      logger.info("Attempting to fix table status validation issues...")

      # Get repository and fix data

      repo = get_table_repo()

      try:

        # Get all tables and fix status issues

        all_tables = await repo.get_all()

        fixes_applied = 0

         

        for table in all_tables:

          table_id = table.get('id')

          current_status = table.get('table_status')

           

          # Fix misspelled status

          if current_status == 'maintence':

            await repo.update(table_id, {'table_status': 'maintenance'})

            fixes_applied += 1

            logger.info(f"Fixed table {table.get('table_number')}: maintence → maintenance")

          elif current_status not in [status.value for status in TableStatus]:

            await repo.update(table_id, {'table_status': 'available'})

            fixes_applied += 1

            logger.info(f"Fixed table {table.get('table_number')}: {current_status} → available")

         

        if fixes_applied > 0:

          logger.info(f"Applied {fixes_applied} table status fixes, retrying request...")

          # Retry the request

          return await tables_endpoint.get_items(

            page=page,

            page_size=page_size,

            filters=filters,

            current_user=current_user

          )

         

      except Exception as fix_error:

        logger.error(f"Failed to fix table status data: {fix_error}")

     

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Failed to get tables list: {str(e)}"

    )





@router.post("", 

       response_model=ApiResponseDTO,

       status_code=status.HTTP_201_CREATED,

       summary="Create table",

       description="Create a new table with QR code")

async def create_table(

  table_data: TableCreateDTO,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Create a new table"""

  return await tables_endpoint.create_item(table_data, current_user)





@router.get("/{table_id}", 

      response_model=TableResponseDTO,

      summary="Get table by ID (Public)",

      description="Get specific table by ID - Public endpoint for QR code access")

async def get_table(

  table_id: str

):

  """Get table by ID - Public endpoint for QR code scanning"""

  # Public endpoint - no authentication required for QR code access

  return await tables_endpoint.get_item(table_id, current_user=None)





@router.put("/{table_id}", 

      response_model=ApiResponseDTO,

      summary="Update table",

      description="Update table information")

async def update_table(

  table_id: str,

  table_update: TableUpdateDTO,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Update table information"""

  return await tables_endpoint.update_item(table_id, table_update, current_user)





@router.delete("/{table_id}", 

        response_model=ApiResponseDTO,

        summary="Delete table",

        description="Deactivate table (soft delete)")

async def delete_table(

  table_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Delete table (soft delete by deactivating)"""

  return await tables_endpoint.delete_item(table_id, current_user, soft_delete=True)





# =============================================================================

# TABLE STATUS MANAGEMENT ENDPOINTS

# =============================================================================



class TableStatusUpdate(BaseModel):

  new_status: TableStatus



@router.put("/{table_id}/status", 

      response_model=ApiResponseDTO,

      summary="Update table status",

      description="Update table status (available, occupied, etc.)")

async def update_table_status(

  table_id: str,

  status_update: TableStatusUpdate,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Update table status"""

  try:

    # Validate request body

    if not status_update or not hasattr(status_update, 'new_status'):

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Request body with 'new_status' field is required"

      )

     

    success = await tables_endpoint.update_table_status(table_id, status_update.new_status, current_user)

     

    if success:

      return ApiResponseDTO(

        success=True,

        message=f"Table status updated to {status_update.new_status.value}"

      )

    else:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Failed to update table status"

      )

       

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error updating table status: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to update table status"

    )





@router.post("/{table_id}/occupy", 

       response_model=ApiResponseDTO,

       summary="Occupy table",

       description="Mark table as occupied")

async def occupy_table(

  table_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Mark table as occupied"""

  try:

    success = await tables_endpoint.update_table_status(

      table_id, TableStatus.OCCUPIED, current_user

    )

     

    if success:

      return ApiResponseDTO(

        success=True,

        message="Table marked as occupied"

      )

    else:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Failed to occupy table"

      )

       

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error occupying table: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to occupy table"

    )





@router.post("/{table_id}/free", 

       response_model=ApiResponseDTO,

       summary="Free table",

       description="Mark table as available")

async def free_table(

  table_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Mark table as available"""

  try:

    success = await tables_endpoint.update_table_status(

      table_id, TableStatus.AVAILABLE, current_user

    )

     

    if success:

      return ApiResponseDTO(

        success=True,

        message="Table marked as available"

      )

    else:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Failed to free table"

      )

       

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error freeing table: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to free table"

    )





# =============================================================================

# QR CODE MANAGEMENT AND PREVIEW ENDPOINTS

# =============================================================================



@router.get("/{table_id}/qr-code", 

      response_model=Dict[str, Any],

      summary="Get table QR code",

      description="Get QR code data for table")

async def get_table_qr_code(

  table_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Get table QR code"""

  try:

    table = await tables_endpoint.get_item(table_id, current_user)

     

    # Decode QR code to get data

    qr_data = tables_endpoint._verify_qr_code(table.qr_code)

     

    if not qr_data:

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Invalid QR code data"

      )

     

    return {

      "table_id": table_id,

      "qr_code": table.qr_code,

      "qr_code_url": table.qr_code_url,

      "venue_id": qr_data.venue_id,

      "table_number": qr_data.table_number

    }

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting table QR code: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get QR code"

    )





@router.post("/{table_id}/regenerate-qr", 

       response_model=ApiResponseDTO,

       summary="Regenerate table QR code",

       description="Regenerate QR code for table")

async def regenerate_table_qr_code(

  table_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Regenerate table QR code"""

  try:

    table = await tables_endpoint.get_item(table_id, current_user)

     

    # Generate new QR code

    new_qr_code = tables_endpoint._generate_qr_code(table.venue_id, table.table_number)

     

    # Update table

    repo = get_table_repo()

    await repo.update(table_id, {

      "qr_code": new_qr_code,

      "qr_code_url": None # Reset URL, will be regenerated

    })

     

    logger.info(f"QR code regenerated for table: {table_id}")

    return ApiResponseDTO(

      success=True,

      message="QR code regenerated successfully",

      data={"qr_code": new_qr_code}

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error regenerating QR code: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to regenerate QR code"

    )





@router.post("/verify-qr", 

       response_model=Dict[str, Any],

       summary="Verify QR code (Public)",

       description="Verify and decode table QR code - Public endpoint")

async def verify_qr_code(

  qr_code: str

):

  """Verify QR code and return table information - Public endpoint"""

  try:

    # Decode QR code

    qr_data = tables_endpoint._verify_qr_code(qr_code)

     

    if not qr_data:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Invalid QR code"

      )

     

    # Get table information (public access)

    table = await tables_endpoint.get_table_by_qr_code(qr_code)

     

    if not table:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Table not found"

      )

     

    # Get venue information

    from app.database.firestore import get_venue_repo

    venue_repo = get_venue_repo()

    venue = await venue_repo.get_by_id(table.venue_id)

     

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    return {

      "valid": True,

      "table": {

        "id": table.id,

        "table_number": table.table_number,

        "capacity": table.capacity,

        "location": table.location,

        "status": table.table_status

      },

      "venue": {

        "id": venue["id"],

        "name": venue["name"],

        "description": venue["description"],

        "is_active": venue.get("is_active", False)

      }

    }

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error verifying QR code: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to verify QR code"

    )





# =============================================================================

# PUBLIC TABLE ACCESS ENDPOINTS (for QR codes)

# =============================================================================



@router.get("/public/{table_id}", 

      response_model=Dict[str, Any],

      summary="Get table info (Public)",

      description="Get table information for public access via QR codes")

async def get_table_public(

  table_id: str

):

  """Get table information for public access (QR code scanning)"""

  try:

    repo = get_table_repo()

    table_data = await repo.get_by_id(table_id)

     

    if not table_data:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Table not found"

      )

     

    # Get venue information

    from app.database.firestore import get_venue_repo

    venue_repo = get_venue_repo()

    venue = await venue_repo.get_by_id(table_data['venue_id'])

     

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Return public table information

    return {

      "table": {

        "id": table_data["id"],

        "table_number": table_data["table_number"],

        "capacity": table_data.get("capacity", 4),

        "location": table_data.get("location"),

        "status": table_data.get("table_status", "available"),

        "qr_code": table_data.get("qr_code")

      },

      "venue": {

        "id": venue["id"],

        "name": venue["name"],

        "description": venue.get("description"),

        "is_active": venue.get("is_active", False)

      }

    }

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting public table info: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get table information"

    )





# =============================================================================

# VENUE TABLE ENDPOINTS

# =============================================================================



@router.get("/venues/{venue_id}/tables", 

      response_model=List[TableResponseDTO],

      summary="Get venue tables",

      description="Get all tables for a specific venue")

async def get_venue_tables(

  venue_id: str,

  status: Optional[TableStatus] = Query(None, description="Filter by status"),

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Get all tables for a venue"""

  try:

    # Validate venue access

    await tables_endpoint._validate_venue_access(venue_id, current_user)

     

    repo = get_table_repo()

     

    if status:

      tables_data = await repo.get_by_status(venue_id, status.value)

    else:

      tables_data = await repo.get_by_venue(venue_id)

     

    # Filter active tables for non-admin users

    from app.core.security import _get_user_role

    user_role = await _get_user_role(current_user)

    if user_role not in ['admin', 'superadmin']:

      tables_data = [table for table in tables_data if table.get('is_active', False)]

     

    # Fix legacy table status data before validation

    processed_tables = []

    for table in tables_data:

      # Fix misspelled 'maintence' to 'maintenance'

      if table.get('table_status') == 'maintence':

        table['table_status'] = 'maintenance'

        # Update in database

        try:

          await repo.update(table['id'], {'table_status': 'maintenance'})

          logger.info(f"Fixed table status for table {table.get('table_number')}: maintence → maintenance")

        except Exception as e:

          logger.error(f"Failed to fix table status for table {table['id']}: {e}")

       

      # Ensure table_status is valid, default to 'available' if invalid

      valid_statuses = [status.value for status in TableStatus]

      if table.get('table_status') not in valid_statuses:

        logger.warning(f"Invalid table status '{table.get('table_status')}' for table {table.get('table_number')}, defaulting to 'available'")

        table['table_status'] = 'available'

        # Update in database

        try:

          await repo.update(table['id'], {'table_status': 'available'})

        except Exception as e:

          logger.error(f"Failed to fix table status for table {table['id']}: {e}")

       

      processed_tables.append(table)

     

    tables = [TableResponseDTO(**table) for table in processed_tables]

     

    logger.info(f"Retrieved {len(tables)} tables for venue: {venue_id}")

    return tables

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting venue tables: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get tables"

    )





@router.get("/venues/{venue_id}/statistics", 

      response_model=Dict[str, Any],

      summary="Get venue table statistics",

      description="Get table statistics for a venue")

async def get_venue_table_statistics(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Get table statistics for a venue"""

  try:

    statistics = await tables_endpoint.get_venue_table_statistics(venue_id, current_user)

     

    logger.info(f"Table statistics retrieved for venue: {venue_id}")

    return statistics

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error getting table statistics: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get table statistics"

    )





# =============================================================================

# BULK OPERATIONS ENDPOINTS

# =============================================================================



@router.post("/bulk-create", 

       response_model=ApiResponseDTO,

       summary="Bulk create tables",

       description="Create multiple tables at once")

async def bulk_create_tables(

  venue_id: str,

  start_number: int = Query(..., ge=1, description="Starting table number"),

  count: int = Query(..., ge=1, le=50, description="Number of tables to create"),

  capacity: int = Query(4, ge=1, le=20, description="Default capacity for all tables"),

  location: Optional[str] = Query(None, description="Default location for all tables"),

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Bulk create tables"""

  try:

    # Validate venue access

    await tables_endpoint._validate_venue_access(venue_id, current_user)

     

    # Check for existing table numbers

    repo = get_table_repo()

    existing_tables = await repo.get_by_venue(venue_id)

    existing_numbers = {table.get('table_number') for table in existing_tables}

     

    # Prepare table data

    tables_to_create = []

    for i in range(count):

      table_number = start_number + i

       

      if table_number in existing_numbers:

        raise HTTPException(

          status_code=status.HTTP_400_BAD_REQUEST,

          detail=f"Table number {table_number} already exists"

        )

       

      table_data = {

        "venue_id": venue_id,

        "table_number": table_number,

        "capacity": capacity,

        "location": location,

        "qr_code": tables_endpoint._generate_qr_code(venue_id, table_number),

        "table_status": TableStatus.AVAILABLE.value,

        "is_active": True

      }

      tables_to_create.append(table_data)

     

    # Bulk create

    created_ids = await repo.create_batch(tables_to_create)

     

    logger.info(f"Bulk created {len(created_ids)} tables for venue: {venue_id}")

    return ApiResponseDTO(

      success=True,

      message=f"Created {len(created_ids)} tables successfully",

      data={"created_count": len(created_ids), "table_ids": created_ids}

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error bulk creating tables: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to create tables"

    )





@router.post("/bulk-update-status", 

       response_model=ApiResponseDTO,

       summary="Bulk update table status",

       description="Update status for multiple tables")

async def bulk_update_table_status(

  table_ids: List[str],

  new_status: TableStatus,

  current_user: Dict[str, Any] = Depends(get_current_admin_user)

):

  """Bulk update table status"""

  try:

    repo = get_table_repo()

     

    # Validate all tables exist and user has access

    for table_id in table_ids:

      table = await repo.get_by_id(table_id)

      if not table:

        raise HTTPException(

          status_code=status.HTTP_404_NOT_FOUND,

          detail=f"Table {table_id} not found"

        )

       

      await tables_endpoint._validate_access_permissions(table, current_user)

     

    # Bulk update

    updates = [(table_id, {"table_status": new_status.value}) for table_id in table_ids]

    await repo.update_batch(updates)

     

    logger.info(f"Bulk updated status for {len(table_ids)} tables to {new_status.value}")

    return ApiResponseDTO(

      success=True,

      message=f"Updated status for {len(table_ids)} tables to {new_status.value}"

    )

     

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Error bulk updating table status: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to update table status"

    )