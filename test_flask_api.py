#!/usr/bin/env python3
"""
Test script to check Flask API endpoints instead of direct SmartAPI usage.
This simulates how your NestJS backend will interact with the Flask worker.
"""

import requests
import time
import json
import uuid
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Flask API base URL
FLASK_API_URL = "http://localhost:5000/api"

# Test credentials (these will be sent to Flask)
TEST_CREDENTIALS = {
    "api_key": os.getenv("API_KEY"),
    "client_code": os.getenv("CLIENT_CODE"),
    "password": os.getenv("PASSWORD"),
    "totp_secret": os.getenv("TOTP_SECRET")
}

# Test tokens
TEST_TOKENS = ["3045", "1594", "11536", "4963", "14366"]

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{FLASK_API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_connect_websocket():
    """Test connecting a WebSocket via Flask API"""
    print("🔗 Testing WebSocket connection...")
    
    websocket_uuid = str(uuid.uuid4())
    payload = {
        "websocket_uuid": websocket_uuid,
        "server_credentials": TEST_CREDENTIALS,
        "tokens": TEST_TOKENS,
        "backend_url": "http://localhost:3000/api/tick"  # Where ticks should be forwarded
    }
    
    try:
        response = requests.post(f"{FLASK_API_URL}/connect", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WebSocket connected: {data}")
            return websocket_uuid, data
        else:
            print(f"❌ Connection failed: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, None

def test_websocket_status():
    """Test getting WebSocket status"""
    print("📊 Testing WebSocket status...")
    try:
        response = requests.get(f"{FLASK_API_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status retrieved: {data}")
            return data
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Status error: {e}")
        return None

def test_disconnect_websocket(websocket_uuid):
    """Test disconnecting a WebSocket"""
    if not websocket_uuid:
        print("⚠️ No WebSocket UUID to disconnect")
        return False
        
    print(f"🔌 Testing WebSocket disconnection for {websocket_uuid}...")
    payload = {"websocket_uuid": websocket_uuid}
    
    try:
        response = requests.post(f"{FLASK_API_URL}/disconnect", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WebSocket disconnected: {data}")
            return True
        else:
            print(f"❌ Disconnection failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Disconnection error: {e}")
        return False

def test_subscribe_tokens(websocket_uuid, auth_data):
    """Test subscribing to additional tokens"""
    if not websocket_uuid or not auth_data:
        print("⚠️ Missing WebSocket UUID or auth data for subscription")
        return False
        
    print(f"📡 Testing token subscription for {websocket_uuid}...")
    
    # Extract auth data from connect response
    auth = auth_data.get("auth", {})
    payload = {
        "websocket_uuid": websocket_uuid,
        "tokens": ["26000", "26009"],  # Additional tokens to test
        "jwt_token": auth.get("jwt_token"),
        "feed_token": auth.get("feed_token"),
        "api_key": auth.get("api_key"),
        "client_code": auth.get("client_code")
    }
    
    try:
        response = requests.post(f"{FLASK_API_URL}/subscribe", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tokens subscribed: {data}")
            return True
        else:
            print(f"❌ Subscription failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Subscription error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Flask API tests...")
    print("=" * 50)
    
    # Check if Flask is running
    if not test_health_check():
        print("❌ Flask app is not running. Start it with: python run.py")
        return
    
    print("\n" + "=" * 50)
    
    # Test WebSocket connection
    websocket_uuid, auth_data = test_connect_websocket()
    
    if websocket_uuid:
        print("\n" + "=" * 50)
        
        # Wait a bit for connection to establish
        print("⏳ Waiting 5 seconds for WebSocket to connect...")
        time.sleep(5)
        
        # Test status
        test_websocket_status()
        
        print("\n" + "=" * 50)
        
        # Test subscription
        test_subscribe_tokens(websocket_uuid, auth_data)
        
        print("\n" + "=" * 50)
        
        # Wait for some ticks
        print("⏳ Waiting 10 seconds to receive ticks...")
        time.sleep(10)
        
        # Test disconnection
        test_disconnect_websocket(websocket_uuid)
    
    print("\n" + "=" * 50)
    print("🏁 Tests completed!")

if __name__ == "__main__":
    main()
