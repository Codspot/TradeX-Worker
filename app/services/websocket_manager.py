import eventlet
import os
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from app.logger import get_logger
from app.config import config
import threading

logger = get_logger(os.getenv("ENV", "development"))

# Global registry for running websockets
_running_websockets = {}

class SmartApiWebSocketManager:
    def __init__(self, websocket_id, credentials, tokens, backend_url=None):
        self.websocket_id = websocket_id
        self.tokens = tokens  # list of up to 50
        self.credentials = credentials  # dict: api_key, client_code, password, totp_secret
        self.backend_url = backend_url or config.BACKEND_WEBHOOK_URL
        self.ws = None
        self._should_run = True
        self._ws_closed = False
        self._last_auth = None

    def start(self):
        # Use credentials from request, not .env
        api_key = self.credentials["api_key"]
        client_code = self.credentials["client_code"]
        password = self.credentials["password"]
        totp_secret = self.credentials["totp_secret"]
        
        # Generate TOTP
        totp = pyotp.TOTP(totp_secret).now()
        smart_api = SmartConnect(api_key)
        session = smart_api.generateSession(client_code, password, totp)
        if not session["status"]:
            logger.error(f"Login failed for websocket_id={self.websocket_id}")
            self._last_auth = None
            return None
            
        jwt_token = session["data"]["jwtToken"]
        feed_token = smart_api.getfeedToken()
        self._last_auth = {
            "jwt_token": jwt_token,
            "feed_token": feed_token,
            "api_key": api_key,
            "client_code": client_code
        }
        
        ws = SmartWebSocketV2(jwt_token, api_key, client_code, feed_token)
        self.ws = ws
        token_list = [{"exchangeType": 1, "tokens": self.tokens}]
        correlation_id = f"ws_{self.websocket_id}"

        def on_open(wsapp):
            logger.info(f"WebSocket connected for {self.websocket_id}")
            ws.subscribe(correlation_id, 1, token_list)

        def on_data(wsapp, message):
            logger.info(f"Tick: {message}")
            self.forward_tick_to_backend(message)

        ws.on_open = on_open
        ws.on_data = on_data
        ws.on_error = lambda wsapp, error: logger.error(f"WebSocket error: {error}")
        ws.on_close = lambda wsapp: logger.info(f"WebSocket closed for {self.websocket_id}")

        logger.info(f"Starting SmartAPI websocket for {self.websocket_id} with {len(self.tokens)} tokens")
        ws.connect()

    def forward_tick_to_backend(self, tick):
        import requests
        from datetime import datetime
        
        # Use the configured backend webhook URL
        backend_tick_url = config.get_backend_tick_url(self.websocket_id)
        
        # Also send to candle processing endpoint
        backend_candle_url = config.get_backend_candle_url()
        
        # Format payload according to LtpDataDto structure
        payload = {
            "websocket_id": self.websocket_id,
            "tick": tick,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Send to websocket endpoint (original behavior)
            response = requests.post(backend_tick_url, json=payload, timeout=2)
            if response.status_code != 200:
                logger.warning(f"Backend websocket returned status {response.status_code}: {response.text}")
                
            # Send to candle processing endpoint (new behavior)
            # Transform tick data for candle processing
            candle_payload = self.transform_tick_for_candle(tick)
            if candle_payload:
                candle_response = requests.post(backend_candle_url, json=candle_payload, timeout=2)
                if candle_response.status_code != 200:
                    logger.warning(f"Backend candle processing returned status {candle_response.status_code}: {candle_response.text}")
                    
        except Exception as e:
            logger.error(f"Failed to forward tick to backend: {e}")
    
    def transform_tick_for_candle(self, tick):
        """Transform SmartAPI tick data to candle processing format"""
        try:
            from datetime import datetime
            # SmartAPI tick format to candle format transformation
            # Adjust this based on your actual SmartAPI tick structure
            return {
                "token": str(tick.get("token", "")),
                "name": tick.get("name", "") or tick.get("symbol", ""),
                "ltp": float(tick.get("ltp", 0)),
                "volume": int(tick.get("volume", 0)),
                "timestamp": tick.get("timestamp") or datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to transform tick for candle processing: {e}")
            return None

    def stop(self):
        self._should_run = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        self._ws_closed = True
        logger.info(f"Stopped SmartAPI websocket for {self.websocket_id}")

    def get_last_auth(self):
        return getattr(self, '_last_auth', None)

# Optionally, add a function to get status for all running websockets

def get_websocket_status():
    return {ws_id: {
        "tokens": ws.tokens,
        "active": ws.ws is not None and not ws._ws_closed
    } for ws_id, ws in _running_websockets.items()}
