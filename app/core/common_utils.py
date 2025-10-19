"""

Common Utilities

Consolidated utilities used across the application

"""

from typing import Dict, Any, List, Optional

from datetime import datetime, timezone

from functools import wraps

from fastapi import HTTPException, status

from  app.core.logging_config import get_logger



logger = get_logger(__name__)





def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:

  """

  Validate that all required fields are present and not empty

   

  Args:

    data: Data dictionary to validate

    required_fields: List of required field names

   

  Returns:

    List of missing field names

  """

  missing_fields = []

   

  for field in required_fields:

    if field not in data or data[field] is None or data[field] == "":

      missing_fields.append(field)

   

  return missing_fields





def raise_validation_error(missing_fields: List[str], custom_message: Optional[str] = None):

  """

  Raise HTTPException for validation errors

   

  Args:

    missing_fields: List of missing field names

    custom_message: Custom error message

  """

  if missing_fields:

    if custom_message:

      detail = custom_message

    else:

      detail = f"Missing required fields: {', '.join(missing_fields)}"

     

    raise HTTPException(

      status_code=status.HTTP_400_BAD_REQUEST,

      detail=detail

    )





def add_timestamps(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:

  """

  Add creation and update timestamps

   

  Args:

    data: Data dictionary to add timestamps to

    is_update: Whether this is an update operation

   

  Returns:

    Data with timestamps added

  """

  now = datetime.now(timezone.utc)

   

  if not is_update:

    data['created_at'] = now

   

  data['updated_at'] = now

  return data





def remove_sensitive_fields(data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:

  """

  Remove sensitive fields from data

   

  Args:

    data: Data dictionary

    sensitive_fields: List of sensitive field names

   

  Returns:

    Data with sensitive fields removed

  """

  if sensitive_fields is None:

    sensitive_fields = ['hashed_password', 'password', 'secret_key']

   

  cleaned_data = data.copy()

  for field in sensitive_fields:

    cleaned_data.pop(field, None)

   

  return cleaned_data





def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:

  """

  Create standardized success response

   

  Args:

    message: Success message

    data: Optional data to include

   

  Returns:

    Standardized response dictionary

  """

  response = {

    "success": True,

    "message": message

  }

  if data is not None:

    response["data"] = data

  return response





def create_error_response(message: str, error_code: str = None, details: Any = None) -> Dict[str, Any]:

  """

  Create standardized error response

   

  Args:

    message: Error message

    error_code: Optional error code

    details: Optional error details

   

  Returns:

    Standardized error response dictionary

  """

  response = {

    "success": False,

    "error": message,

    "timestamp": datetime.now(timezone.utc).isoformat()

  }

  if error_code:

    response["error_code"] = error_code

  if details:

    response["details"] = details

  return response





async def get_or_404(repo, entity_id: str, entity_name: str = "Entity") -> Dict[str, Any]:

  """

  Get entity by ID or raise 404

   

  Args:

    repo: Repository instance

    entity_id: Entity ID

    entity_name: Entity name for error message

   

  Returns:

    Entity data

   

  Raises:

    HTTPException: If entity not found

  """

  entity = await repo.get_by_id(entity_id)

  if not entity:

    raise HTTPException(

      status_code=status.HTTP_404_NOT_FOUND,

      detail=f"{entity_name} not found"

    )

  return entity





def paginate_list(data: List[Dict[str, Any]], page: int = 1, page_size: int = 20) -> tuple:

  """

  Paginate a list of data

   

  Args:

    data: List of data to paginate

    page: Page number (1-based)

    page_size: Number of items per page

   

  Returns:

    Tuple of (paginated_data, pagination_info)

  """

  total = len(data)

  start = (page - 1) * page_size

  end = start + page_size

  paginated_data = data[start:end]

   

  pagination_info = {

    "page": page,

    "page_size": page_size,

    "total": total,

    "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,

    "has_next": page * page_size < total,

    "has_prev": page > 1

  }

   

  return paginated_data, pagination_info





def apply_search_filter(data: List[Dict[str, Any]], search: str, search_fields: List[str]) -> List[Dict[str, Any]]:

  """

  Apply search filter to data

   

  Args:

    data: List of data to search

    search: Search term

    search_fields: Fields to search in

   

  Returns:

    Filtered data

  """

  if not search:

    return data

   

  search_lower = search.lower()

  filtered_data = []

   

  for item in data:

    for field in search_fields:

      field_value = item.get(field, "")

      if isinstance(field_value, str) and search_lower in field_value.lower():

        filtered_data.append(item)

        break

   

  return filtered_data





def log_operation(operation: str, entity_id: str = None, **kwargs):

  """

  Log service operations consistently

   

  Args:

    operation: Operation description

    entity_id: Optional entity ID

    **kwargs: Additional log data

  """

  log_data = {"operation": operation}

  if entity_id:

    log_data["entity_id"] = entity_id

  log_data.update(kwargs)

   

  logger.info(f"{operation} completed", extra=log_data)





# =============================================================================

# ROLE AND PERMISSION UTILITIES (from generic_utils.py)

# =============================================================================



async def validate_user_role(

  current_user: Dict[str, Any], 

  required_roles: List[str],

  error_message: str = "Insufficient permissions"

) -> str:

  """

  Generic role validation utility

   

  Args:

    current_user: Current user data

    required_roles: List of roles that are allowed

    error_message: Custom error message

     

  Returns:

    str: User's role

     

  Raises:

    HTTPException: If user doesn't have required role

  """

  if not current_user:

    raise HTTPException(

      status_code=status.HTTP_401_UNAUTHORIZED,

      detail="Authentication required"

    )

   

  from  app.core.security import _get_user_role

  user_role = await _get_user_role(current_user)

   

  if user_role not in required_roles:

    raise HTTPException(

      status_code=status.HTTP_403_FORBIDDEN,

      detail=error_message

    )

   

  return user_role





async def validate_admin_or_superadmin(current_user: Dict[str, Any]) -> str:

  """Validate that user is admin or superadmin"""

  return await validate_user_role(

    current_user, 

    ["admin", "superadmin"], 

    "Admin or superadmin role required"

  )





async def safe_get_resource(

  repo: Any,

  resource_id: str,

  resource_name: str = "Resource"

) -> Dict[str, Any]:

  """

  Safely get a resource by ID with consistent error handling

   

  Args:

    repo: Repository instance

    resource_id: ID of resource to get

    resource_name: Name of resource for error messages

     

  Returns:

    Dict[str, Any]: Resource data

     

  Raises:

    HTTPException: If resource not found

  """

  resource = await repo.get_by_id(resource_id)

  if not resource:

    raise HTTPException(

      status_code=status.HTTP_404_NOT_FOUND,

      detail=f"{resource_name} not found"

    )

  return resource





async def validate_unique_field(

  repo: Any,

  field_name: str,

  field_value: str,

  exclude_id: Optional[str] = None,

  error_message: str = None

) -> None:

  """

  Validate that a field value is unique in the repository

   

  Args:

    repo: Repository instance

    field_name: Name of the field to check

    field_value: Value to check for uniqueness

    exclude_id: Optional ID to exclude from check (for updates)

    error_message: Custom error message

     

  Raises:

    HTTPException: If field value is not unique

  """

  if not field_value:

    return

     

  # Query for existing records with this field value

  existing_items = await repo.query([(field_name, '==', field_value)])

   

  # If updating, exclude the current item

  if exclude_id and existing_items:

    existing_items = [item for item in existing_items if item.get('id') != exclude_id]

   

  if existing_items:

    if not error_message:

      error_message = f"{field_name.replace('_', ' ').title()} already exists"

    raise HTTPException(

      status_code=status.HTTP_400_BAD_REQUEST,

      detail=error_message

    )





def apply_pagination(data: List[Dict[str, Any]], page: int = 1, page_size: int = 20) -> tuple:

  """

  Apply pagination to data and return pagination metadata

   

  Args:

    data: List of data to paginate

    page: Page number (1-based)

    page_size: Number of items per page

     

  Returns:

    Tuple of (paginated_data, pagination_metadata)

  """

  total = len(data)

  start = (page - 1) * page_size

  end = start + page_size

  paginated_data = data[start:end]

   

  pagination_meta = {

    "page": page,

    "page_size": page_size,

    "total": total,

    "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,

    "has_next": page * page_size < total,

    "has_prev": page > 1

  }

   

  return paginated_data, pagination_meta





def handle_endpoint_errors(operation_name: str):

  """

  Decorator for handling endpoint errors consistently

   

  Args:

    operation_name: Name of the operation for logging

     

  Returns:

    Decorator function

  """

  def decorator(func):

    @wraps(func)

    async def wrapper(*args, **kwargs):

      try:

        logger.info(f"Starting {operation_name}")

        result = await func(*args, **kwargs)

        logger.info(f"Completed {operation_name}")

        return result

      except HTTPException:

        # Re-raise HTTP exceptions as-is

        raise

      except Exception as e:

        logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)

        raise HTTPException(

          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

          detail=f"Internal server error in {operation_name}"

        )

    return wrapper

  return decorator