"""

Generic Endpoint Utilities

Provides reusable endpoint patterns to eliminate duplication

"""

from typing import Dict, Any, Optional, List, Type, TypeVar

from fastapi import HTTPException, status, Query

from  app.models.dto import ApiResponseDTO, PaginatedResponseDTO

from  app.core.common_utils import (

  handle_endpoint_errors, safe_get_resource, validate_unique_field,

  apply_pagination, create_success_response

)

from app.core.logging_config import get_logger



logger = get_logger(__name__)



T = TypeVar('T')



# =============================================================================

# GENERIC CRUD ENDPOINTS

# =============================================================================



async def generic_get_items(

  repo: Any,

  page: int,

  page_size: int,

  filters: Optional[Dict[str, Any]] = None,

  search: Optional[str] = None,

  dto_class: Optional[Type[T]] = None,

  current_user: Optional[Dict[str, Any]] = None

) -> PaginatedResponseDTO:

  """

  Generic get items with pagination

   

  Args:

    repo: Repository instance

    page: Page number

    page_size: Items per page

    filters: Filters to apply

    search: Search term

    dto_class: DTO class to convert items to

    current_user: Current user for filtering

     

  Returns:

    PaginatedResponseDTO: Paginated response

  """

  # Build query filters

  query_filters = []

  if filters:

    for field, value in filters.items():

      if value is not None:

        query_filters.append((field, '==', value))

   

  # Get items

  if search:

    # Use search method if available

    search_method = getattr(repo, 'search_text', None)

    if search_method:

      items = await search_method(

        search_fields=['name', 'description'],

        search_term=search,

        additional_filters=query_filters,

        limit=1000

      )

    else:

      items = await repo.query(query_filters)

      # Apply client-side search

      search_lower = search.lower()

      items = [

        item for item in items

        if search_lower in item.get('name', '').lower() or

          search_lower in item.get('description', '').lower()

      ]

  else:

    items = await repo.query(query_filters)

   

  # Apply pagination

  paginated_items, pagination_meta = apply_pagination(items, page, page_size)

   

  # Convert to DTOs if class provided

  if dto_class:

    paginated_items = [dto_class(**item) for item in paginated_items]

   

  return PaginatedResponseDTO(

    success=True,

    data=paginated_items,

    **pagination_meta

  )





async def generic_create_item(

  repo: Any,

  item_data: Dict[str, Any],

  dto_class: Optional[Type[T]] = None,

  validation_func: Optional[callable] = None,

  prepare_data_func: Optional[callable] = None,

  current_user: Optional[Dict[str, Any]] = None

) -> ApiResponseDTO:

  """

  Generic create item

   

  Args:

    repo: Repository instance

    item_data: Data to create

    dto_class: DTO class to convert result to

    validation_func: Optional validation function

    prepare_data_func: Optional data preparation function

    current_user: Current user

     

  Returns:

    ApiResponseDTO: Success response with created item

  """

  # Prepare data if function provided

  if prepare_data_func:

    item_data = await prepare_data_func(item_data, current_user)

   

  # Validate if function provided

  if validation_func:

    await validation_func(item_data, current_user)

   

  # Create item

  item_id = await repo.create(item_data)

   

  # Get created item

  created_item = await repo.get_by_id(item_id)

   

  # Convert to DTO if class provided

  if dto_class:

    created_item = dto_class(**created_item)

   

  return create_success_response(

    message="Item created successfully",

    data=created_item

  )





async def generic_update_item(

  repo: Any,

  item_id: str,

  update_data: Dict[str, Any],

  dto_class: Optional[Type[T]] = None,

  validation_func: Optional[callable] = None,

  current_user: Optional[Dict[str, Any]] = None,

  resource_name: str = "Item"

) -> ApiResponseDTO:

  """

  Generic update item

   

  Args:

    repo: Repository instance

    item_id: ID of item to update

    update_data: Data to update

    dto_class: DTO class to convert result to

    validation_func: Optional validation function

    current_user: Current user

    resource_name: Name of resource for messages

     

  Returns:

    ApiResponseDTO: Success response with updated item

  """

  # Get existing item

  existing_item = await safe_get_resource(repo, item_id, resource_name)

   

  # Validate if function provided

  if validation_func:

    await validation_func(existing_item, current_user)

   

  # Update item

  await repo.update(item_id, update_data)

   

  # Get updated item

  updated_item = await repo.get_by_id(item_id)

   

  # Convert to DTO if class provided

  if dto_class:

    updated_item = dto_class(**updated_item)

   

  return create_success_response(

    message=f"{resource_name} updated successfully",

    data=updated_item

  )





async def generic_delete_item(

  repo: Any,

  item_id: str,

  validation_func: Optional[callable] = None,

  current_user: Optional[Dict[str, Any]] = None,

  resource_name: str = "Item",

  soft_delete: bool = True

) -> ApiResponseDTO:

  """

  Generic delete item

   

  Args:

    repo: Repository instance

    item_id: ID of item to delete

    validation_func: Optional validation function

    current_user: Current user

    resource_name: Name of resource for messages

    soft_delete: Whether to soft delete (deactivate) or hard delete

     

  Returns:

    ApiResponseDTO: Success response

  """

  # Get existing item

  existing_item = await safe_get_resource(repo, item_id, resource_name)

   

  # Validate if function provided

  if validation_func:

    await validation_func(existing_item, current_user)

   

  # Delete item

  if soft_delete:

    await repo.update(item_id, {"is_active": False})

    message = f"{resource_name} deactivated successfully"

  else:

    await repo.delete(item_id)

    message = f"{resource_name} deleted successfully"

   

  return create_success_response(message=message)





# =============================================================================

# COMMON ENDPOINT PATTERNS

# =============================================================================



def create_standard_crud_endpoints(

  router,

  endpoint_instance,

  dto_create_class,

  dto_update_class,

  dto_response_class,

  resource_name: str,

  base_path: str = ""

):

  """

  Create standard CRUD endpoints for a resource

   

  Args:

    router: FastAPI router

    endpoint_instance: Endpoint class instance

    dto_create_class: Create DTO class

    dto_update_class: Update DTO class

    dto_response_class: Response DTO class

    resource_name: Name of the resource

    base_path: Base path for endpoints

  """

   

  @router.get(f"{base_path}/", response_model=PaginatedResponseDTO)

  @handle_endpoint_errors(f"Get {resource_name.lower()}s")

  async def get_items(

    page: int = Query(1, ge=1),

    page_size: int = Query(10, ge=1, le=100),

    search: Optional[str] = Query(None),

    current_user: Dict[str, Any] = None # Dependency injection handled by caller

  ):

    return await endpoint_instance.get_items(

      page=page,

      page_size=page_size,

      search=search,

      current_user=current_user

    )

   

  @router.post(f"{base_path}/", response_model=ApiResponseDTO, status_code=201)

  @handle_endpoint_errors(f"Create {resource_name.lower()}")

  async def create_item(

    item_data: dto_create_class,

    current_user: Dict[str, Any] = None # Dependency injection handled by caller

  ):

    return await endpoint_instance.create_item(item_data, current_user)

   

  @router.get(f"{base_path}/{{item_id}}", response_model=dto_response_class)

  @handle_endpoint_errors(f"Get {resource_name.lower()}")

  async def get_item(

    item_id: str,

    current_user: Dict[str, Any] = None # Dependency injection handled by caller

  ):

    return await endpoint_instance.get_item(item_id, current_user)

   

  @router.put(f"{base_path}/{{item_id}}", response_model=ApiResponseDTO)

  @handle_endpoint_errors(f"Update {resource_name.lower()}")

  async def update_item(

    item_id: str,

    update_data: dto_update_class,

    current_user: Dict[str, Any] = None # Dependency injection handled by caller

  ):

    return await endpoint_instance.update_item(item_id, update_data, current_user)

   

  @router.delete(f"{base_path}/{{item_id}}", response_model=ApiResponseDTO)

  @handle_endpoint_errors(f"Delete {resource_name.lower()}")

  async def delete_item(

    item_id: str,

    current_user: Dict[str, Any] = None # Dependency injection handled by caller

  ):

    return await endpoint_instance.delete_item(item_id, current_user, soft_delete=True)





# =============================================================================

# VALIDATION HELPERS

# =============================================================================



async def validate_email_uniqueness(

  repo: Any,

  email: str,

  exclude_id: Optional[str] = None

) -> None:

  """Validate email uniqueness"""

  await validate_unique_field(

    repo=repo,

    field_name="email",

    field_value=email,

    exclude_id=exclude_id,

    error_message="Email already in use"

  )





async def validate_phone_uniqueness(

  repo: Any,

  phone: str,

  exclude_id: Optional[str] = None

) -> None:

  """Validate phone uniqueness"""

  await validate_unique_field(

    repo=repo,

    field_name="phone",

    field_value=phone,

    exclude_id=exclude_id,

    error_message="Phone number already in use"

  )





async def validate_name_uniqueness(

  repo: Any,

  name: str,

  exclude_id: Optional[str] = None

) -> None:

  """Validate name uniqueness"""

  await validate_unique_field(

    repo=repo,

    field_name="name",

    field_value=name,

    exclude_id=exclude_id,

    error_message="Name already exists"

  )