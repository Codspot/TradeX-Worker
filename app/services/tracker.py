import os
import eventlet
from app.logger import get_logger
from app.services.websocket_manager import SmartApiWebSocketManager, _running_websockets

logger = get_logger(os.getenv("ENV", "development"))

def start_tracking(websocket_id, credentials, tokens):
    if websocket_id in _running_websockets:
        logger.info(f"WebSocket for {websocket_id} already running, skipping start.")
        return
    manager = SmartApiWebSocketManager(websocket_id, credentials, tokens)
    _running_websockets[websocket_id] = manager
    eventlet.spawn_n(manager.start)

def stop_tracking(websocket_id):
    manager = _running_websockets.pop(websocket_id, None)
    if manager:
        manager.stop()
