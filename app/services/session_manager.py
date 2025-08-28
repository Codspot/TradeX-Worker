import os
import pyotp
from datetime import datetime, timedelta
from dotenv import load_dotenv
from SmartApi import SmartConnect

load_dotenv()

class AngelOneSessionManager:
    _session_data = None
    _session_created_at = None

    @classmethod
    def get_session(cls):
        # If session exists and is valid, reuse it
        if cls._session_data and cls._is_session_valid():
            return cls._session_data

        # Create new session
        return cls._create_new_session()

    @classmethod
    def _create_new_session(cls):
        # Load env vars
        api_key = os.getenv("API_KEY")
        client_code = os.getenv("CLIENT_CODE")
        password = os.getenv("PASSWORD")
        totp_secret = os.getenv("TOTP_SECRET")

        smart_api = SmartConnect(api_key)
        totp = pyotp.TOTP(totp_secret).now()
        session = smart_api.generateSession(client_code, password, totp)

        if not session["status"]:
            raise Exception("Login failed")

        jwt_token = session["data"]["jwtToken"]
        refresh_token = session["data"]["refreshToken"]
        feed_token = smart_api.getfeedToken()

        cls._session_data = {
            "smart_api": smart_api,
            "jwt_token": jwt_token,
            "refresh_token": refresh_token,
            "feed_token": feed_token
        }
        cls._session_created_at = datetime.now()
        return cls._session_data

    @classmethod
    def _is_session_valid(cls):
        if not cls._session_data or not cls._session_created_at:
            return False
        
        # Check if all required tokens exist
        if not all(k in cls._session_data for k in ("jwt_token", "feed_token", "smart_api")):
            return False
        
        # Check if session is older than 20 hours (JWT expires in 24h, be safe)
        session_age = datetime.now() - cls._session_created_at
        if session_age > timedelta(hours=20):
            return False
        
        return True

    @classmethod
    def reset_session(cls):
        cls._session_data = None
        cls._session_created_at = None

    @classmethod
    def ensure_session(cls):
        # Helper to always return a valid session, retrying if needed
        try:
            return cls.get_session()
        except Exception as e:
            cls.reset_session()
            return cls.get_session()
