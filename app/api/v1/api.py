"""

Dino Multi-Venue Platform - Main API Router

Simplified router with core endpoints and roles/permissions

"""

from fastapi import APIRouter

from  app.core.logging_config import get_logger



logger = get_logger(__name__)



# Import core endpoints

from app.api.v1.endpoints import (
    user,
    venue, 
    workspace,
    menu,
    table,
    order,
    auth,
    health,
    roles,
    permissions,
    dashboard,
    analytics,
    user_preferences,
    venue_status,
    table_areas,
    user_data,
    websocket,
    tour
)



api_router = APIRouter()



# =============================================================================

# CORE MANAGEMENT ENDPOINTS

# =============================================================================



# User Management

api_router.include_router(

  user.router, 

  prefix="/users", 

  tags=["users"],

  responses={

    404: {"description": "User not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Venue Management

api_router.include_router(

  venue.router, 

  prefix="/venues", 

  tags=["venues"],

  responses={

    404: {"description": "Venue not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Workspace Management

api_router.include_router(

  workspace.router, 

  prefix="/workspaces", 

  tags=["workspaces"]

)



# Menu Management

api_router.include_router(

  menu.router, 

  prefix="/menu", 

  tags=["menu"],

  responses={

    404: {"description": "Menu item/category not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Table Management

api_router.include_router(

  table.router, 

  prefix="/tables", 

  tags=["tables"],

  responses={

    404: {"description": "Table not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Order Management

api_router.include_router(

  order.router, 

  prefix="/orders", 

  tags=["orders"],

  responses={

    404: {"description": "Order not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# =============================================================================

# AUTHENTICATION ENDPOINTS

# =============================================================================



# Authentication & Registration

api_router.include_router(

  auth.router, 

  prefix="/auth", 

  tags=["authentication"],

  responses={

    401: {"description": "Authentication failed"},

    400: {"description": "Invalid credentials"},

    409: {"description": "User already exists"}

  }

)



# User Data Management

api_router.include_router(

  user_data.router, 

  prefix="/auth", 

  tags=["user-data"],

  responses={

    404: {"description": "User data not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Health Check Endpoints

api_router.include_router(

  health.router, 

  prefix="/health",

  tags=["health"],

  responses={

    200: {"description": "Health check successful"},

    503: {"description": "Service unavailable"}

  }

)



# =============================================================================

# ROLE AND PERMISSION MANAGEMENT ENDPOINTS

# =============================================================================



# Roles Management

api_router.include_router(

  roles.router, 

  prefix="/roles", 

  tags=["roles"],

  responses={

    404: {"description": "Role not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"},

    400: {"description": "Invalid role data"}

  }

)



# Permissions Management

api_router.include_router(

  permissions.router, 

  prefix="/permissions", 

  tags=["permissions"],

  responses={

    404: {"description": "Permission not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"},

    400: {"description": "Invalid permission data"}

  }

)



# =============================================================================

# DASHBOARD ENDPOINTS

# =============================================================================



# Dashboard Management

api_router.include_router(

  dashboard.router, 

  tags=["dashboard"],

  responses={

    404: {"description": "Dashboard data not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"},

    400: {"description": "No venue assigned"}

  }

)



# =============================================================================

# ANALYTICS ENDPOINTS

# =============================================================================



# Analytics Management

api_router.include_router(

  analytics.router, 

  prefix="/analytics",

  tags=["analytics"],

  responses={

    404: {"description": "Analytics data not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"},

    400: {"description": "Invalid parameters"}

  }

)



# =============================================================================

# ADDITIONAL UTILITY ENDPOINTS

# =============================================================================



# User Preferences and Addresses

api_router.include_router(

  user_preferences.router, 

  prefix="/users/me", 

  tags=["user-preferences"],

  responses={

    404: {"description": "User not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Venue Status Management

api_router.include_router(

  venue_status.router, 

  prefix="/venues", 

  tags=["venue-status"],

  responses={

    404: {"description": "Venue not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)



# Table Areas Management

api_router.include_router(

  table_areas.router, 

  prefix="/table-areas", 

  tags=["table-areas"],

  responses={

    404: {"description": "Area not found"},

    403: {"description": "Access denied"},

    401: {"description": "Authentication required"}

  }

)

# =============================================================================
# TOUR MANAGEMENT ENDPOINTS
# =============================================================================

# Dashboard Tour Management
api_router.include_router(
    tour.router, 
    prefix="/tour", 
    tags=["tour"],
    responses={
        404: {"description": "Tour data not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# =============================================================================
# TOUR MANAGEMENT ENDPOINTS
# =============================================================================

# Dashboard Tour Management
api_router.include_router(
    tour.router, 
    prefix="/tour", 
    tags=["tour"],
    responses={
        404: {"description": "Tour data not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

# WebSocket Real-time Updates
api_router.include_router(
    websocket.router, 
    prefix="/ws", 
    tags=["websocket"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        1008: {"description": "WebSocket authentication failed"}
    }
)

