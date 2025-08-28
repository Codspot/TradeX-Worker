# run.py
import eventlet
eventlet.monkey_patch()  # ✅ MUST BE FIRST

from app import create_app
from socket_server import socketio

app = create_app()

if __name__ == "__main__":
    print("🚀 Running Flask + WebSocket on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
