from flask import Blueprint, request, jsonify
from datetime import datetime
from app.services.tracker import (
    start_tracking,
    stop_tracking
)
from app.services.websocket_manager import get_websocket_status, SmartApiWebSocketManager, _running_websockets

api = Blueprint("api", __name__)

# New endpoint: connect a websocket with credentials and up to 50 tokens (updated for backend integration)
@api.route("/connect", methods=["POST"])
def connect():
    try:
        data = request.get_json()
        websocket_uuid = data.get("websocket_uuid")
        server_credentials = data.get("server_credentials")  # dict: api_key, client_code, password, totp_secret
        tokens = data.get("tokens", [])  # list of up to 50 instrument tokens
        backend_url = data.get("backend_url", "http://localhost:5001")  # where to send ticks
        
        if not server_credentials or not websocket_uuid or not tokens:
            return jsonify({"success": False, "error": "server_credentials, websocket_uuid, and tokens required"}), 400
            
        # Check if websocket is already connected
        if websocket_uuid in _running_websockets:
            return jsonify({"success": False, "error": "WebSocket already connected"}), 400
            
        # Create and start the WebSocket manager asynchronously
        manager = SmartApiWebSocketManager(websocket_uuid, server_credentials, tokens, backend_url)
        _running_websockets[websocket_uuid] = manager
        
        # Start connection in background - don't wait for it
        import eventlet
        eventlet.spawn_n(manager.start)
        
        # Return immediately with accepted status
        return jsonify({
            "success": True, 
            "message": f"WebSocket {websocket_uuid} connection initiated",
            "tokens_count": len(tokens),
            "status": "connecting"
        }), 202  # 202 Accepted - request accepted for processing
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 500

# New endpoint: disconnect all websockets
@api.route("/disconnect-all", methods=["POST"])
def disconnect_all():
    try:
        disconnected_count = 0
        for websocket_uuid in list(_running_websockets.keys()):
            stop_tracking(websocket_uuid)
            disconnected_count += 1
            
        return jsonify({
            "success": True, 
            "message": f"Disconnected {disconnected_count} websocket(s)"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Disconnect failed: {str(e)}"}), 500

# New endpoint: disconnect a websocket by websocket_id
@api.route("/disconnect", methods=["POST"])
def disconnect():
    data = request.get_json()
    websocket_id = data.get("websocket_id")
    if not websocket_id:
        return jsonify({"error": "websocket_id required"}), 400
    stop_tracking(websocket_id)
    return jsonify({"message": "WebSocket stopped"})

# New endpoint: subscribe to tokens using auth/session info
@api.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    websocket_id = data.get("websocket_id")
    tokens = data.get("tokens", [])
    jwt_token = data.get("jwt_token")
    feed_token = data.get("feed_token")
    api_key = data.get("api_key")
    client_code = data.get("client_code")
    if not websocket_id or not tokens or not jwt_token or not feed_token or not api_key or not client_code:
        return jsonify({"error": "websocket_id, tokens, jwt_token, feed_token, api_key, client_code required"}), 400
    # Find the manager and subscribe to new tokens
    manager = _running_websockets.get(websocket_id)
    if not manager:
        return jsonify({"error": "WebSocket not found"}), 404
    # Subscribe to new tokens
    try:
        ws = manager.ws
        if ws is None:
            return jsonify({"error": "WebSocket not connected"}), 400
        token_list = [{"exchangeType": 1, "tokens": tokens}]
        correlation_id = f"ws_{websocket_id}"
        ws.subscribe(correlation_id, 1, token_list)
        manager.tokens = tokens
        return jsonify({"message": "Subscribed to tokens"})
    except Exception as e:
        return jsonify({"error": f"Failed to subscribe: {e}"}), 500

# Optional: status endpoint
@api.route("/status", methods=["GET"])
def status():
    """Get status of all WebSocket connections"""
    websocket_statuses = {}
    
    for ws_id, manager in _running_websockets.items():
        auth = manager.get_last_auth()
        is_connected = manager.ws is not None and not manager._ws_closed
        
        websocket_statuses[ws_id] = {
            "tokens": manager.tokens,
            "tokens_count": len(manager.tokens) if manager.tokens else 0,
            "active": is_connected,
            "authenticated": bool(auth),
            "status": "connected" if (auth and is_connected) else "connecting",
            "backend_url": manager.backend_url
        }
    
    return jsonify({
        "total_websockets": len(_running_websockets),
        "websockets": websocket_statuses
    })

# Health check endpoint for PM2 and load balancers
@api.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "smartapi-worker",
        "timestamp": datetime.now().isoformat(),
        "active_websockets": len(_running_websockets)
    })

# New endpoint: check connection status for a specific websocket
@api.route("/connection-status/<websocket_uuid>", methods=["GET"])
def connection_status(websocket_uuid):
    try:
        manager = _running_websockets.get(websocket_uuid)
        if not manager:
            return jsonify({
                "success": False,
                "websocket_uuid": websocket_uuid,
                "status": "not_found",
                "message": "WebSocket not found"
            }), 404
            
        # Check if authenticated
        auth = manager.get_last_auth()
        is_connected = manager.ws is not None and not manager._ws_closed
        
        return jsonify({
            "success": True,
            "websocket_uuid": websocket_uuid,
            "status": "connected" if (auth and is_connected) else "connecting",
            "authenticated": bool(auth),
            "active": is_connected,
            "tokens_count": len(manager.tokens) if manager.tokens else 0,
            "auth_data": auth if auth else None
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "websocket_uuid": websocket_uuid,
            "status": "error",
            "error": str(e)
        }), 500
