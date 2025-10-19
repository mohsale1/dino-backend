"""

WebSocket Endpoints for Real-time Updates

Handles WebSocket connections for venue users and order notifications

"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status

from typing import Optional

import asyncio



from app.core.websocket_manager import connection_manager, authenticate_websocket_user

from app.core.logging_config import get_logger



logger = get_logger(__name__)

router = APIRouter()





@router.websocket("/")

async def root_websocket_endpoint(

    websocket: WebSocket,

    token: Optional[str] = Query(None, description="JWT authentication token"),

    venue_id: Optional[str] = Query(None, description="Venue ID for venue-specific connection"),

    user_id: Optional[str] = Query(None, description="User ID for user-specific connection")

):

    """

    Root WebSocket endpoint that can handle both venue and user connections

    

    Usage:

    - For venue connection: /ws?venue_id=VENUE_ID&token=TOKEN

    - For user connection: /ws?user_id=USER_ID&token=TOKEN

    """

    try:

        # Check if JWT auth is disabled (development mode)

        from app.core.config import settings

        if not settings.is_jwt_auth_enabled:

            # Use development user

            from app.core.security import get_development_user

            user_data = await get_development_user()

            logger.info("Using development user for WebSocket connection")

        else:

            # Authenticate user with JWT

            if not token:

                await websocket.close(code=1008, reason="Authentication token required")

                return

            

            user_data = await authenticate_websocket_user(token)

            if not user_data:

                await websocket.close(code=1008, reason="Invalid authentication token")

                return

        

        # Determine connection type

        if venue_id:

            # Venue connection

            # Check if user has access to this venue

            user_venue_id = user_data.get("venue_id")

            user_role = user_data.get("role")

            

            # SuperAdmin can access any venue, others must match venue_id

            if user_role != "superadmin" and user_venue_id != venue_id:

                await websocket.close(code=1008, reason="Access denied to this venue")

                return

            

            # Validate venue exists

            from app.core.dependency_injection import get_repository_manager

            repo_manager = get_repository_manager()

            venue_repo = repo_manager.get_repository('venue')

            

            venue = await venue_repo.get_by_id(venue_id)

            if not venue:

                await websocket.close(code=1008, reason="Venue not found")

                return

            

            if not venue.get("is_active", False):

                await websocket.close(code=1008, reason="Venue is not active")

                return

            

            # Connect to venue WebSocket

            await connection_manager.connect_to_venue(websocket, venue_id, user_data)

            logger.info(f"User {user_data.get('email')} connected to venue {venue_id} WebSocket via root endpoint")

            

        elif user_id:

            # User connection

            # Check if user can access this user_id

            authenticated_user_id = user_data.get("id")

            user_role = user_data.get("role")

            

            # Users can only access their own WebSocket, unless they're superadmin

            if user_role != "superadmin" and authenticated_user_id != user_id:

                await websocket.close(code=1008, reason="Access denied")

                return

            

            # Connect to user WebSocket

            await connection_manager.connect_user(websocket, user_id, user_data)

            logger.info(f"User {user_data.get('email')} connected to personal WebSocket via root endpoint")

            

        else:

            await websocket.close(code=1008, reason="Either venue_id or user_id must be provided")

            return

        

        # Keep connection alive and handle messages

        while True:

            try:

                # Wait for messages from client

                message = await websocket.receive_text()

                await connection_manager.handle_message(websocket, message)

                

            except WebSocketDisconnect:

                logger.info(f"User {user_data.get('email')} disconnected from WebSocket")

                break

            except Exception as e:

                logger.error(f"Error in root WebSocket: {e}")

                break

    

    except WebSocketDisconnect:

        logger.info("WebSocket disconnected")

    except Exception as e:

        logger.error(f"Root WebSocket error: {e}")

        if websocket.client_state.name != "DISCONNECTED":

            await websocket.close(code=1011, reason="Internal server error")

    

    finally:

        # Clean up connection

        await connection_manager.disconnect(websocket)





@router.websocket("/venue/{venue_id}")

async def venue_websocket_endpoint(

    websocket: WebSocket,

    venue_id: str,

    token: Optional[str] = Query(None, description="JWT authentication token")

):

    """

    WebSocket endpoint for venue-specific real-time updates

    

    Connects users to a venue's real-time feed for:

    - New order notifications

    - Order status updates

    - Table status changes

    - System notifications

    """

    user_data = None

    

    try:

        # Check if JWT auth is disabled (development mode)

        from app.core.config import settings

        if not settings.is_jwt_auth_enabled:

            # Use development user

            from app.core.security import get_development_user

            user_data = await get_development_user()

            logger.info("Using development user for WebSocket connection")

        else:

            # Authenticate user with JWT

            if not token:

                await websocket.close(code=1008, reason="Authentication token required")

                return

            

            user_data = await authenticate_websocket_user(token)

            if not user_data:

                await websocket.close(code=1008, reason="Invalid authentication token")

                return

        

        # Check if user has access to this venue

        user_venue_id = user_data.get("venue_id")

        user_role = user_data.get("role")

        

        # SuperAdmin can access any venue, others must match venue_id

        if user_role != "superadmin" and user_venue_id != venue_id:

            await websocket.close(code=1008, reason="Access denied to this venue")

            return

        

        # Validate venue exists

        from app.core.dependency_injection import get_repository_manager

        repo_manager = get_repository_manager()

        venue_repo = repo_manager.get_repository('venue')

        

        venue = await venue_repo.get_by_id(venue_id)

        if not venue:

            await websocket.close(code=1008, reason="Venue not found")

            return

        

        if not venue.get("is_active", False):

            await websocket.close(code=1008, reason="Venue is not active")

            return

        

        # Connect to venue WebSocket

        await connection_manager.connect_to_venue(websocket, venue_id, user_data)

        

        logger.info(f"User {user_data.get('email')} connected to venue {venue_id} WebSocket")

        

        # Keep connection alive and handle messages

        while True:

            try:

                # Wait for messages from client

                message = await websocket.receive_text()

                await connection_manager.handle_message(websocket, message)

                

            except WebSocketDisconnect:

                logger.info(f"User {user_data.get('email')} disconnected from venue {venue_id}")

                break

            except Exception as e:

                logger.error(f"Error in venue WebSocket: {e}")

                break

    

    except WebSocketDisconnect:

        logger.info(f"WebSocket disconnected for venue {venue_id}")

    except Exception as e:

        logger.error(f"Venue WebSocket error: {e}")

        if websocket.client_state.name != "DISCONNECTED":

            await websocket.close(code=1011, reason="Internal server error")

    

    finally:

        # Clean up connection

        await connection_manager.disconnect(websocket)





@router.websocket("/user/{user_id}")

async def user_websocket_endpoint(

    websocket: WebSocket,

    user_id: str,

    token: Optional[str] = Query(None, description="JWT authentication token")

):

    """

    WebSocket endpoint for user-specific notifications

    

    Connects users to their personal notification feed for:

    - Personal notifications

    - Account updates

    - System messages

    """

    user_data = None

    

    try:

        # Check if JWT auth is disabled (development mode)

        from app.core.config import settings

        if not settings.is_jwt_auth_enabled:

            # Use development user

            from app.core.security import get_development_user

            user_data = await get_development_user()

            logger.info("Using development user for WebSocket connection")

        else:

            # Authenticate user with JWT

            if not token:

                await websocket.close(code=1008, reason="Authentication token required")

                return

            

            user_data = await authenticate_websocket_user(token)

            if not user_data:

                await websocket.close(code=1008, reason="Invalid authentication token")

                return

        

        # Check if user can access this user_id

        authenticated_user_id = user_data.get("id")

        user_role = user_data.get("role")

        

        # Users can only access their own WebSocket, unless they're superadmin

        if user_role != "superadmin" and authenticated_user_id != user_id:

            await websocket.close(code=1008, reason="Access denied")

            return

        

        # Connect to user WebSocket

        await connection_manager.connect_user(websocket, user_id, user_data)

        

        logger.info(f"User {user_data.get('email')} connected to personal WebSocket")

        

        # Keep connection alive and handle messages

        while True:

            try:

                # Wait for messages from client

                message = await websocket.receive_text()

                await connection_manager.handle_message(websocket, message)

                

            except WebSocketDisconnect:

                logger.info(f"User {user_data.get('email')} disconnected from personal WebSocket")

                break

            except Exception as e:

                logger.error(f"Error in user WebSocket: {e}")

                break

    

    except WebSocketDisconnect:

        logger.info(f"WebSocket disconnected for user {user_id}")

    except Exception as e:

        logger.error(f"User WebSocket error: {e}")

        if websocket.client_state.name != "DISCONNECTED":

            await websocket.close(code=1011, reason="Internal server error")

    

    finally:

        # Clean up connection

        await connection_manager.disconnect(websocket)





# =============================================================================

# WEBSOCKET MANAGEMENT ENDPOINTS (HTTP)

# =============================================================================



@router.get("/stats")

async def get_websocket_stats():

    """Get WebSocket connection statistics"""

    try:

        stats = connection_manager.get_connection_stats()

        return {

            "success": True,

            "data": stats

        }

    except Exception as e:

        logger.error(f"Error getting WebSocket stats: {e}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to get WebSocket statistics"

        )





@router.post("/venue/{venue_id}/notify")

async def send_venue_notification(

    venue_id: str,

    notification_data: dict

):

    """

    Send notification to all users connected to a venue

    (For testing and admin purposes)

    """

    try:

        notification_type = notification_data.get("type", "system_notification")

        title = notification_data.get("title", "System Notification")

        message = notification_data.get("message", "")

        data = notification_data.get("data", {})

        

        await connection_manager.send_system_notification(

            venue_id, notification_type, title, message, data

        )

        

        return {

            "success": True,

            "message": f"Notification sent to venue {venue_id}"

        }

        

    except Exception as e:

        logger.error(f"Error sending venue notification: {e}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to send notification"

        )





@router.post("/user/{user_id}/notify")

async def send_user_notification(

    user_id: str,

    notification_data: dict

):

    """

    Send notification to specific user

    (For testing and admin purposes)

    """

    try:

        await connection_manager.send_to_user(user_id, notification_data)

        

        return {

            "success": True,

            "message": f"Notification sent to user {user_id}"

        }

        

    except Exception as e:

        logger.error(f"Error sending user notification: {e}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to send notification"

        )





@router.get("/venue/{venue_id}/connections")

async def get_venue_connections(venue_id: str):

    """Get number of active connections for a venue"""

    try:

        count = connection_manager.get_venue_connections_count(venue_id)

        return {

            "success": True,

            "data": {

                "venue_id": venue_id,

                "active_connections": count

            }

        }

    except Exception as e:

        logger.error(f"Error getting venue connections: {e}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to get venue connections"

        )





@router.get("/auth-status")

async def get_websocket_auth_status():

    """Get WebSocket authentication status for debugging"""

    from app.core.config import settings

    return {

        "success": True,

        "data": {

            "jwt_auth_enabled": settings.is_jwt_auth_enabled,

            "environment": settings.ENVIRONMENT,

            "auth_mode": "JWT" if settings.is_jwt_auth_enabled else "Development",

            "dev_user_id": settings.DEV_USER_ID if not settings.is_jwt_auth_enabled else None,

            "websocket_endpoints": {

                "venue": "/api/v1/ws/venue/{venue_id}",

                "user": "/api/v1/ws/user/{user_id}",

                "token_required": settings.is_jwt_auth_enabled

            }

        }

    }





@router.post("/test/order-notification")

async def test_order_notification(test_data: dict):

    """Test endpoint to send a sample order notification"""

    try:

        venue_id = test_data.get("venue_id")

        if not venue_id:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="venue_id is required"

            )

        

        # Create sample order data

        sample_order = {

            "id": "test-order-123",

            "order_number": "ORD-TEST-001",

            "venue_id": venue_id,

            "total_amount": 25.50,

            "table_id": "test-table-1",

            "table_number": "T1",

            "status": "pending",

            "payment_status": "pending",

            "customer_name": "Test Customer",

            "items": [

                {"name": "Test Item", "quantity": 2, "price": 12.75}

            ],

            "created_at": "2024-01-01T12:00:00Z"

        }

        

        # Send test notification

        await connection_manager.send_order_notification(sample_order, "order_created")

        

        logger.info(f"Test notification sent to venue {venue_id} with {connection_manager.get_venue_connections_count(venue_id)} active connections")

        

        return {

            "success": True,

            "message": f"Test order notification sent to venue {venue_id}",

            "data": sample_order,

            "active_connections": connection_manager.get_venue_connections_count(venue_id)

        }

        

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error sending test notification: {e}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to send test notification"

        )