# run.py
import eventlet
eventlet.monkey_patch()  # ✅ MUST BE FIRST

from app import create_app
from app.config import config
from socket_server import socketio

app = create_app()

if __name__ == "__main__":
    print(f"🚀 SmartAPI Worker starting with configuration:")
    print(f"   Environment: {config.ENV}")
    print(f"   Worker: http://{config.WORKER_HOST}:{config.WORKER_PORT}")
    print(f"   Backend: {config.BACKEND_BASE_URL}")
    print(f"   Webhook: {config.BACKEND_WEBHOOK_URL}")
    print(f"   API Key: {config.SMARTAPI_API_KEY[:8]}*** (from env)")
    
    socketio.run(app, host=config.WORKER_HOST, port=config.WORKER_PORT)
