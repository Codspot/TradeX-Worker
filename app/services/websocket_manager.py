import eventlet
import os
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from app.logger import get_logger
from app.config import config
import threading
import json
from datetime import datetime

logger = get_logger(os.getenv("ENV", "development"))

# Create a separate logger for tick analysis
tick_analysis_logger = get_logger("tick_analysis")

# Global registry for running websockets
_running_websockets = {}

# Session statistics
session_stats = {
    'start_time': datetime.now(),
    'total_ticks': 0,
    'successful_forwards': 0,
    'failed_forwards': 0,
    'unique_tokens': set(),
    'total_volume': 0,
    'price_range': {'min': float('inf'), 'max': 0}
}

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
            # Log tick to both console and file with detailed analysis
            self.log_tick_analysis(message)
            self.forward_tick_to_backend(message)

        ws.on_open = on_open
        ws.on_data = on_data
        ws.on_error = lambda wsapp, error: logger.error(f"WebSocket error: {error}")
        ws.on_close = lambda wsapp: logger.info(f"WebSocket closed for {self.websocket_id}")

        logger.info(f"Starting SmartAPI websocket for {self.websocket_id} with {len(self.tokens)} tokens")
        
        # Log session start
        tick_analysis_logger.info(f"🚀 SESSION START - WebSocket {self.websocket_id} | Tokens: {len(self.tokens)} | Time: {datetime.now().isoformat()}")
        
        ws.connect()

    def log_tick_analysis(self, tick):
        """Enhanced tick logging for analysis"""
        try:
            global session_stats
            session_stats['total_ticks'] += 1
            
            # Extract tick data
            token = str(tick.get('token', 'UNKNOWN'))
            ltp_paise = tick.get('last_traded_price', 0)
            ltp_rupees = ltp_paise / 100.0 if ltp_paise else 0.0
            volume = tick.get('volume_trade_for_the_day', 0)
            exchange_timestamp = tick.get('exchange_timestamp', 0)
            subscription_mode = tick.get('subscription_mode_val', 'UNKNOWN')
            
            # Update session stats
            session_stats['unique_tokens'].add(token)
            session_stats['total_volume'] += volume
            if ltp_rupees > 0:
                session_stats['price_range']['min'] = min(session_stats['price_range']['min'], ltp_rupees)
                session_stats['price_range']['max'] = max(session_stats['price_range']['max'], ltp_rupees)
            
            # Create detailed log entry
            log_entry = {
                'session_id': self.websocket_id,
                'tick_count': session_stats['total_ticks'],
                'timestamp': datetime.now().isoformat(),
                'token': token,
                'ltp_paise': ltp_paise,
                'ltp_rupees': round(ltp_rupees, 2),
                'volume': volume,
                'exchange_timestamp': exchange_timestamp,
                'subscription_mode': subscription_mode,
                'raw_tick': tick
            }
            
            # Console log (simplified)
            logger.info(f"📊 TICK #{session_stats['total_ticks']:>6} | Token: {token:>5} | LTP: ₹{ltp_rupees:>8.2f} | Vol: {volume:>8} | {subscription_mode}")
            
            # File log (detailed JSON)
            tick_analysis_logger.info(f"TICK_DATA: {json.dumps(log_entry, default=str)}")
            
            # Every 100 ticks, log session summary
            if session_stats['total_ticks'] % 100 == 0:
                self.log_session_summary()
                
        except Exception as e:
            logger.error(f"Error in tick analysis logging: {e}")

    def log_session_summary(self):
        """Log session statistics summary"""
        try:
            global session_stats
            duration = datetime.now() - session_stats['start_time']
            
            summary = {
                'session_id': self.websocket_id,
                'duration_seconds': duration.total_seconds(),
                'total_ticks': session_stats['total_ticks'],
                'unique_tokens': len(session_stats['unique_tokens']),
                'total_volume': session_stats['total_volume'],
                'successful_forwards': session_stats['successful_forwards'],
                'failed_forwards': session_stats['failed_forwards'],
                'success_rate': round((session_stats['successful_forwards'] / max(1, session_stats['total_ticks'])) * 100, 2),
                'ticks_per_second': round(session_stats['total_ticks'] / max(1, duration.total_seconds()), 2),
                'price_range': session_stats['price_range'] if session_stats['price_range']['min'] != float('inf') else None
            }
            
            logger.info(f"📈 SESSION SUMMARY: Ticks: {summary['total_ticks']} | Tokens: {summary['unique_tokens']} | Success: {summary['success_rate']}% | TPS: {summary['ticks_per_second']}")
            tick_analysis_logger.info(f"SESSION_SUMMARY: {json.dumps(summary, default=str)}")
            
        except Exception as e:
            logger.error(f"Error in session summary logging: {e}")

    def forward_tick_to_backend(self, tick):
        import requests
        from datetime import datetime
        
        global session_stats
        
        # Only send to candle processing endpoint (no duplicate calls)
        backend_candle_url = config.get_backend_candle_url()
        
        # Transform tick data for candle processing
        candle_payload = self.transform_tick_for_candle(tick)
        if candle_payload:
            try:
                start_time = datetime.now()
                candle_response = requests.post(backend_candle_url, json=candle_payload, timeout=2)
                response_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
                
                if candle_response.status_code not in [200, 201]:
                    session_stats['failed_forwards'] += 1
                    logger.warning(f"❌ Backend candle processing failed | Status: {candle_response.status_code} | Token: {candle_payload.get('token')} | Response: {candle_response.text}")
                    tick_analysis_logger.warning(f"FORWARD_FAILED: Token={candle_payload.get('token')}, Status={candle_response.status_code}, Response={candle_response.text}")
                else:
                    session_stats['successful_forwards'] += 1
                    logger.debug(f"✅ Tick forwarded successfully | Token: {candle_payload.get('token')} | LTP: ₹{candle_payload.get('ltp')} | Response time: {response_time:.1f}ms")
                    tick_analysis_logger.debug(f"FORWARD_SUCCESS: Token={candle_payload.get('token')}, LTP={candle_payload.get('ltp')}, ResponseTime={response_time:.1f}ms")
                    
            except Exception as e:
                session_stats['failed_forwards'] += 1
                logger.error(f"❌ Failed to forward tick to backend | Token: {candle_payload.get('token', 'UNKNOWN')} | Error: {e}")
                tick_analysis_logger.error(f"FORWARD_ERROR: Token={candle_payload.get('token', 'UNKNOWN')}, Error={str(e)}")
        else:
            logger.warning(f"⚠️ Failed to transform tick data for token: {tick.get('token', 'UNKNOWN')}")
            tick_analysis_logger.warning(f"TRANSFORM_FAILED: {json.dumps(tick, default=str)}")
    
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
