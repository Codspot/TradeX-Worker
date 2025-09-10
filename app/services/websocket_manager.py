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
        
        # Only send to candle processing endpoint (no duplicate calls)
        backend_candle_url = config.get_backend_candle_url()
        
        # Transform tick data for candle processing
        candle_payload = self.transform_tick_for_candle(tick)
        if candle_payload:
            try:
                candle_response = requests.post(backend_candle_url, json=candle_payload, timeout=2)
                if candle_response.status_code not in [200, 201]:
                    logger.warning(f"Backend candle processing returned status {candle_response.status_code}: {candle_response.text}")
                else:
                    logger.debug(f"Successfully sent tick to candle processing: Token={candle_payload.get('token')}, LTP={candle_payload.get('ltp')}")
            except Exception as e:
                logger.error(f"Failed to forward tick to backend candle processing: {e}")
    
    def transform_tick_for_candle(self, tick):
        """Transform SmartAPI tick data to candle processing format"""
        try:
            from datetime import datetime
            
            # SmartAPI tick format to candle format transformation
            # Extract LTP from last_traded_price and convert paise to rupees
            ltp_paise = tick.get("last_traded_price", 0)
            ltp_rupees = ltp_paise / 100.0 if ltp_paise else 0.0
            
            return {
                "token": str(tick.get("token", "")),
                "name": tick.get("tradingsymbol", "") or tick.get("symbol", "") or f"Token-{tick.get('token', 'unknown')}",
                "ltp": ltp_rupees,  # Convert paise to rupees
                "volume": int(tick.get("volume_trade_for_the_day", 0)),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to transform tick for candle processing: {e}")
            logger.error(f"Tick data: {tick}")
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
