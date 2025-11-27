"""
WebSocket Endpoints for Real-time Updates
Handles WebSocket connections for venue users and order notifications
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from typing import Optional
import asyncio

from app.core.websocket import connection_manager, authenticate_websocket_user
from app.core.logging import get_logger

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
            from app.core.dependencies import get_repository_manager
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
        from app.core.dependencies import get_repository_manager
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