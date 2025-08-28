import os
import json
import websocket
import threading
import time
import sys
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# Read credentials from environment variables
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# Check for missing credentials
missing = []
if not API_KEY:
    missing.append("API_KEY")
if not CLIENT_CODE:
    missing.append("CLIENT_CODE")
if not PASSWORD:
    missing.append("PASSWORD")
if not TOTP_SECRET:
    missing.append("TOTP_SECRET")
if missing:
    print(f"Error: Missing environment variables: {', '.join(missing)}")
    print("\nSet them using:\n  export API_KEY=your_api_key\n  export CLIENT_CODE=your_client_code\n  export PASSWORD=your_password\n  export TOTP_SECRET=your_totp_secret\n")
    sys.exit(1)

# Generate TOTP
current_totp = pyotp.TOTP(TOTP_SECRET).now()

# Login and get tokens
smart_api = SmartConnect(API_KEY)
session = smart_api.generateSession(CLIENT_CODE, PASSWORD, current_totp)
if not session["status"]:
    print("Login failed:", session)
    sys.exit(1)
print("Login successful",session)
FEED_TOKEN = smart_api.getfeedToken()
JWT_TOKEN = session["data"]["jwtToken"]

# List your 5 tokens here (example tokens)
TOKENS = ["3045", "2885", "26009", "26017", "26037"]
EXCHANGE_TYPE = 1  # 1 for NSE

def on_open(wsapp):
    print("WebSocket opened")
    wsapp.subscribe("test_correlation_id", 1, [{"exchangeType": EXCHANGE_TYPE, "tokens": TOKENS}])

def on_data(wsapp, message):
    print("Tick:", message)

def on_error(wsapp, error):
    print("Error:", error)

def on_close(wsapp):
    print("WebSocket closed")

if __name__ == "__main__":
    # Defensive: close all other SmartWebSocketV2 connections before starting
    import gc
    for obj in gc.get_objects():
        try:
            if isinstance(obj, SmartWebSocketV2):
                try:
                    obj.close()
                except Exception:
                    pass
        except Exception:
            pass
    ws = SmartWebSocketV2(JWT_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN)
    ws.on_open = on_open
    ws.on_data = on_data
    ws.on_error = on_error
    ws.on_close = on_close
    ws.connect()