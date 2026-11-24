import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("ws_router")
router = APIRouter()

@router.websocket("/ws/events/{event_id}")
async def websocket_event_seat_stream(websocket: WebSocket, event_id: int):
    """
    WebSocket endpoint for real-time seat lock, release, and reservation notifications.
    Clients viewing the seat map receive push events immediately without polling.
    """
    await ws_manager.connect(event_id, websocket)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "event_id": event_id,
            "message": f"Subscribed to real-time seat updates for event {event_id}",
        })
        while True:
            # Keep connection open and receive any client heartbeats/messages
            data = await websocket.receive_text()
            # Respond to client ping if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(event_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on event {event_id}: {e}")
        ws_manager.disconnect(event_id, websocket)
