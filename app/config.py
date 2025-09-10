"""
Configuration module for SmartAPI Worker
Loads environment variables and provides default values
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for SmartAPI Worker"""
    
    # Environment
    ENV = os.getenv('ENV', 'development')
    
    # Backend Configuration
    BACKEND_BASE_URL = os.getenv('BACKEND_BASE_URL', 'http://localhost:3000')
    BACKEND_WEBHOOK_URL = os.getenv('BACKEND_WEBHOOK_URL', 'http://localhost:3000/api/websocket')
    
    # SmartAPI Worker Configuration
    WORKER_HOST = os.getenv('WORKER_HOST', '0.0.0.0')
    WORKER_PORT = int(os.getenv('WORKER_PORT', 5000))
    
    # SmartAPI Credentials (can be overridden via API)
    SMARTAPI_API_KEY = os.getenv('API_KEY', '')
    SMARTAPI_CLIENT_CODE = os.getenv('CLIENT_CODE', '')
    SMARTAPI_PASSWORD = os.getenv('PASSWORD', '')
    SMARTAPI_TOTP_SECRET = os.getenv('TOTP_SECRET', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_backend_tick_url(cls, websocket_id):
        """Get the backend webhook URL for tick data"""
        return f"{cls.BACKEND_WEBHOOK_URL}/{websocket_id}/ltp"
    
    @classmethod
    def get_backend_candle_url(cls):
        """Get the backend webhook URL for candle data"""
        return f"{cls.BACKEND_BASE_URL}/api/in-memory-candles/process-tick"
    
    @classmethod
    def display_config(cls):
        """Display current configuration (without sensitive data)"""
        return {
            'ENV': cls.ENV,
            'BACKEND_BASE_URL': cls.BACKEND_BASE_URL,
            'BACKEND_WEBHOOK_URL': cls.BACKEND_WEBHOOK_URL,
            'WORKER_HOST': cls.WORKER_HOST,
            'WORKER_PORT': cls.WORKER_PORT,
            'SMARTAPI_API_KEY': cls.SMARTAPI_API_KEY[:8] + '***' if cls.SMARTAPI_API_KEY else 'Will be provided via API',
            'SMARTAPI_CLIENT_CODE': cls.SMARTAPI_CLIENT_CODE[:4] + '***' if cls.SMARTAPI_CLIENT_CODE else 'Will be provided via API',
            'LOG_LEVEL': cls.LOG_LEVEL
        }

# Create a global config instance
config = Config()
