"""
WebSocket Connection Manager
Handles real-time connections for venue users and order notifications
"""
import json
import asyncio
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

from app.core.logging_config import get_logger
from app.core.security import verify_token

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store active connections by venue
        self.venue_connections: Dict[str, Set[WebSocket]] = {}
        
        # Store user connections with metadata
        self.user_connections: Dict[str, Dict[str, Any]] = {}
        
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect_to_venue(self, websocket: WebSocket, venue_id: str, user_data: Dict[str, Any]):
        """Connect user to venue WebSocket for real-time updates"""
        await websocket.accept()
        
        # Add to venue connections
        if venue_id not in self.venue_connections:
            self.venue_connections[venue_id] = set()
        
        self.venue_connections[venue_id].add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user_data.get("id"),
            "venue_id": venue_id,
            "user_role": user_data.get("role"),
            "workspace_id": user_data.get("workspace_id"),
            "connected_at": datetime.utcnow(),
            "connection_type": "venue"
        }
        
        # Store user connection
        user_id = user_data.get("id")
        if user_id:
            self.user_connections[user_id] = {
                "websocket": websocket,
                "venue_id": venue_id,
                "role": user_data.get("role"),
                "connected_at": datetime.utcnow()
            }
        
        logger.info(f"User {user_data.get('email', 'unknown')} connected to venue {venue_id} WebSocket")
        
        # Send connection confirmation
        await self.send_to_connection(websocket, {
            "type": "connection_established",
            "data": {
                "venue_id": venue_id,
                "user_id": user_data.get("id"),
                "message": "Connected to venue real-time updates"
            }
        })
    
    async def connect_user(self, websocket: WebSocket, user_id: str, user_data: Dict[str, Any]):
        """Connect user for personal notifications"""
        await websocket.accept()
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "user_role": user_data.get("role"),
            "workspace_id": user_data.get("workspace_id"),
            "connected_at": datetime.utcnow(),
            "connection_type": "user"
        }
        
        # Store user connection
        self.user_connections[user_id] = {
            "websocket": websocket,
            "role": user_data.get("role"),
            "connected_at": datetime.utcnow()
        }
        
        logger.info(f"User {user_data.get('email', 'unknown')} connected to personal WebSocket")
        
        # Send connection confirmation
        await self.send_to_connection(websocket, {
            "type": "connection_established",
            "data": {
                "user_id": user_id,
                "message": "Connected to personal notifications"
            }
        })
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect WebSocket and clean up"""
        metadata = self.connection_metadata.get(websocket)
        
        if metadata:
            venue_id = metadata.get("venue_id")
            user_id = metadata.get("user_id")
            
            # Remove from venue connections
            if venue_id and venue_id in self.venue_connections:
                self.venue_connections[venue_id].discard(websocket)
                if not self.venue_connections[venue_id]:
                    del self.venue_connections[venue_id]
            
            # Remove from user connections
            if user_id and user_id in self.user_connections:
                if self.user_connections[user_id].get("websocket") == websocket:
                    del self.user_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {e}")
            # Remove failed connection
            await self.disconnect(websocket)
    
    async def send_to_venue(self, venue_id: str, message: Dict[str, Any], role_filter: Optional[List[str]] = None):
        """Send message to all users connected to a venue"""
        if venue_id not in self.venue_connections:
            logger.warning(f"No active connections for venue {venue_id}")
            return
        
        connections_to_remove = []
        sent_count = 0
        
        for websocket in self.venue_connections[venue_id].copy():
            try:
                # Check role filter if specified
                metadata = self.connection_metadata.get(websocket)
                if role_filter and metadata:
                    user_role = metadata.get("user_role")
                    if user_role not in role_filter:
                        continue
                
                await websocket.send_text(json.dumps(message, default=str))
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send message to venue WebSocket: {e}")
                connections_to_remove.append(websocket)
        
        # Clean up failed connections
        for websocket in connections_to_remove:
            await self.disconnect(websocket)
        
        logger.info(f"Sent message to {sent_count} users in venue {venue_id}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"User {user_id} not connected to WebSocket")
            return
        
        connection_info = self.user_connections[user_id]
        websocket = connection_info["websocket"]
        
        try:
            await websocket.send_text(json.dumps(message, default=str))
            logger.info(f"Sent message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            await self.disconnect(websocket)
    
    async def send_order_notification(self, order_data: Dict[str, Any], notification_type: str = "order_created"):
        """Send order notification to venue users"""
        venue_id = order_data.get("venue_id")
        if not venue_id:
            logger.warning("Order notification: No venue_id provided")
            return
        
        # Create notification message
        message = {
            "type": notification_type,
            "data": {
                "order_id": order_data.get("id"),
                "order_number": order_data.get("order_number"),
                "venue_id": venue_id,
                "total_amount": order_data.get("total_amount", 0),
                "table_id": order_data.get("table_id"),
                "table_number": order_data.get("table_number"),
                "status": order_data.get("status"),
                "payment_status": order_data.get("payment_status"),
                "customer_name": order_data.get("customer_name"),
                "items_count": len(order_data.get("items", [])),
                "created_at": order_data.get("created_at"),
                "estimated_ready_time": order_data.get("estimated_ready_time")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to venue staff (admin, operator roles)
        await self.send_to_venue(venue_id, message, role_filter=["admin", "operator", "superadmin"])
        
        logger.info(f"Order notification sent for order {order_data.get('order_number')} in venue {venue_id}")
    
    async def send_order_status_update(self, order_data: Dict[str, Any], old_status: str, new_status: str):
        """Send order status update notification"""
        venue_id = order_data.get("venue_id")
        if not venue_id:
            return
        
        message = {
            "type": "order_status_updated",
            "data": {
                "order_id": order_data.get("id"),
                "order_number": order_data.get("order_number"),
                "venue_id": venue_id,
                "old_status": old_status,
                "new_status": new_status,
                "table_number": order_data.get("table_number"),
                "updated_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all venue users
        await self.send_to_venue(venue_id, message)
        
        logger.info(f"Order status update sent: {order_data.get('order_number')} {old_status} -> {new_status}")
    
    async def send_table_status_update(self, table_data: Dict[str, Any], old_status: str, new_status: str):
        """Send table status update notification"""
        venue_id = table_data.get("venue_id")
        if not venue_id:
            return
        
        message = {
            "type": "table_status_updated",
            "data": {
                "table_id": table_data.get("id"),
                "table_number": table_data.get("table_number"),
                "venue_id": venue_id,
                "old_status": old_status,
                "new_status": new_status,
                "capacity": table_data.get("capacity"),
                "updated_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_venue(venue_id, message)
        
        logger.info(f"Table status update sent: Table {table_data.get('table_number')} {old_status} -> {new_status}")
    
    async def send_system_notification(self, venue_id: str, notification_type: str, title: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Send system notification to venue"""
        notification = {
            "type": "system_notification",
            "data": {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "venue_id": venue_id,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.send_to_venue(venue_id, notification)
        
        logger.info(f"System notification sent to venue {venue_id}: {title}")
    
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            metadata = self.connection_metadata.get(websocket)
            if not metadata:
                return
            
            user_id = metadata.get("user_id")
            venue_id = metadata.get("venue_id")
            
            # Handle different message types
            if message_type == "ping":
                await self.send_to_connection(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "get_venue_status" and venue_id:
                # Send current venue status
                await self.send_venue_status(websocket, venue_id)
            
            elif message_type == "get_notifications" and user_id:
                # Send user notifications
                await self.send_user_notifications(websocket, user_id)
            
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket message")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def send_venue_status(self, websocket: WebSocket, venue_id: str):
        """Send current venue status to WebSocket"""
        try:
            # Get venue status from database
            from app.core.dependency_injection import get_repository_manager
            
            repo_manager = get_repository_manager()
            order_repo = repo_manager.get_repository('order')
            table_repo = repo_manager.get_repository('table')
            
            # Get active orders
            orders = await order_repo.get_by_venue_id(venue_id)
            active_orders = [
                order for order in orders 
                if order.get('status') in ['pending', 'confirmed', 'preparing', 'ready']
            ]
            
            # Get tables
            tables = await table_repo.get_by_venue(venue_id)
            
            status_data = {
                "type": "venue_status",
                "data": {
                    "venue_id": venue_id,
                    "active_orders_count": len(active_orders),
                    "total_tables": len(tables),
                    "occupied_tables": len([t for t in tables if t.get('table_status') == 'occupied']),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await self.send_to_connection(websocket, status_data)
            
        except Exception as e:
            logger.error(f"Error sending venue status: {e}")
    
    async def send_user_notifications(self, websocket: WebSocket, user_id: str):
        """Send user notifications to WebSocket"""
        try:
            # This would integrate with a notification system
            # For now, send empty notifications
            notifications_data = {
                "type": "notifications",
                "data": {
                    "user_id": user_id,
                    "notifications": [],
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await self.send_to_connection(websocket, notifications_data)
            
        except Exception as e:
            logger.error(f"Error sending user notifications: {e}")
    
    def get_venue_connections_count(self, venue_id: str) -> int:
        """Get number of active connections for a venue"""
        return len(self.venue_connections.get(venue_id, set()))
    
    def get_total_connections_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_metadata)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        venue_stats = {}
        for venue_id, connections in self.venue_connections.items():
            venue_stats[venue_id] = len(connections)
        
        return {
            "total_connections": self.get_total_connections_count(),
            "venue_connections": venue_stats,
            "user_connections": len(self.user_connections),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global connection manager instance
connection_manager = ConnectionManager()


async def authenticate_websocket_user(token: str) -> Optional[Dict[str, Any]]:
    """Authenticate WebSocket connection using JWT token"""
    try:
        if not token:
            return None
        
        # Decode JWT token
        payload = verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user data from database
        from app.core.dependency_injection import get_repository_manager
        
        repo_manager = get_repository_manager()
        user_repo = repo_manager.get_repository('user')
        
        user_data = await user_repo.get_by_id(user_id)
        if not user_data or not user_data.get("is_active", False):
            return None
        
        return user_data
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None
