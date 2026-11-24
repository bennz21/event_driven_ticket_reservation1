import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")

class ConnectionManager:
    """
    Manages active WebSocket connections grouped by event_id.
    Broadcasts real-time seat lock, release, and reservation status to all viewing clients.
    """
    def __init__(self) -> None:
        # Map event_id -> Set of active WebSockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, event_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = set()
        self.active_connections[event_id].add(websocket)
        logger.info(f"Client connected to event {event_id}. Total connected: {len(self.active_connections[event_id])}")

    def disconnect(self, event_id: int, websocket: WebSocket) -> None:
        if event_id in self.active_connections:
            self.active_connections[event_id].discard(websocket)
            if not self.active_connections[event_id]:
                del self.active_connections[event_id]
        logger.info(f"Client disconnected from event {event_id}.")

    async def broadcast(self, event_id: int, message: dict) -> None:
        """Broadcasts a JSON message to all clients viewing the specified event."""
        if event_id not in self.active_connections:
            return
        
        dead_connections = set()
        for websocket in list(self.active_connections[event_id]):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client in event {event_id}: {e}")
                dead_connections.add(websocket)
        
        for dead_ws in dead_connections:
            self.disconnect(event_id, dead_ws)

ws_manager = ConnectionManager()
