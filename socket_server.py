from flask_socketio import SocketIO
from flask import request
from app.services.tracker import start_tracking, stop_tracking
import time

socketio = SocketIO(cors_allowed_origins="*")  # Will be initialized later

# Maps: sid => set(symboltokens)
subscriptions = {}

# Track how many clients are watching a symbol
watching_count = {}  # symboltoken => int

def init_socketio(app):
    socketio.init_app(app)

    @socketio.on("connect")
    def on_connect():
        subscriptions[request.sid] = set()

    @socketio.on("disconnect")
    def on_disconnect():
        if request.sid in subscriptions:
            for symboltoken in subscriptions[request.sid]:
                _decrement_watching(symboltoken)
            subscriptions.pop(request.sid, None)

    @socketio.on("subscribe")
    def on_subscribe(data):
        symboltoken = str(data.get("symboltoken"))
        exchangeType = data.get("exchangeType", 1)
        interval = data.get("interval", 1)

        previous_tokens = subscriptions.get(request.sid, set()).copy()
        print(f"[SOCKET] SID {request.sid} subscribing to {symboltoken}, previous: {previous_tokens}")
        for prev in previous_tokens:
            if prev != symboltoken:
                _decrement_watching(prev)
                subscriptions[request.sid].discard(prev)
                # Do NOT disconnect backend/frontend socket, just close SmartAPI socket
                stop_tracking(prev)
                time.sleep(2)  # Shorter delay, since SmartAPI socket is closed only

        if symboltoken in previous_tokens:
            print(f"[SOCKET] SID {request.sid} already subscribed to {symboltoken}")
            return

        subscriptions.setdefault(request.sid, set()).add(symboltoken)
        print(f"[SOCKET] SID {request.sid} subscriptions after subscribe: {subscriptions[request.sid]}")

        if watching_count.get(symboltoken, 0) == 0:
            start_tracking(symboltoken=symboltoken, exchangeType=exchangeType, interval_min=interval)

        watching_count[symboltoken] = watching_count.get(symboltoken, 0) + 1

    @socketio.on("unsubscribe")
    def on_unsubscribe(data):
        symboltoken = str(data.get("symboltoken"))
        if request.sid in subscriptions and symboltoken in subscriptions[request.sid]:
            subscriptions[request.sid].discard(symboltoken)
            print(f"[SOCKET] SID {request.sid} unsubscribed from {symboltoken}")
            print(f"[SOCKET] SID {request.sid} subscriptions after unsubscribe: {subscriptions[request.sid]}")
            # Only close SmartAPI socket, not backend/frontend socket
            _decrement_watching(symboltoken)

def _decrement_watching(symboltoken):
    if symboltoken in watching_count:
        watching_count[symboltoken] -= 1
        if watching_count[symboltoken] <= 0:
            stop_tracking(symboltoken)
            watching_count.pop(symboltoken)

# At module level, after socketio = ...
def emit_tick_to_clients(tick):
    # Broadcast tick to all clients subscribed to this symboltoken
    symboltoken = tick.get("symboltoken")
    for sid, tokens in subscriptions.items():
        if symboltoken in tokens:
            socketio.emit("tick", tick, room=sid)
