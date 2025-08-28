from flask import Blueprint, request, jsonify
from app.services.tracker import (
    start_tracking,
    stop_tracking
)
from app.services.websocket_manager import get_websocket_status, SmartApiWebSocketManager, _running_websockets

api = Blueprint("api", __name__)

# New endpoint: connect a websocket with credentials and up to 50 tokens
@api.route("/connect", methods=["POST"])
def connect():
    data = request.get_json()
    credentials = data.get("credentials")  # dict: api_key, client_code, etc.
    websocket_id = data.get("websocket_id")
    tokens = data.get("tokens", [])  # list of up to 50
    if not credentials or not websocket_id or not tokens:
        return jsonify({"error": "credentials, websocket_id, and tokens required"}), 400
    manager = SmartApiWebSocketManager(websocket_id, credentials, tokens)
    _running_websockets[websocket_id] = manager
    # Start and get auth tokens
    manager.start()
    auth = manager.get_last_auth()
    if not auth:
        return jsonify({"error": "Login failed"}), 401
    return jsonify({"message": "WebSocket started", "auth": auth})

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
    status = get_websocket_status()
    return jsonify(status)
