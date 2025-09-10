#!/usr/bin/env python3
"""
Mock backend server to receive ticks from Flask worker.
This simulates your NestJS backend receiving tick data.
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Store received ticks for testing
received_ticks = []

@app.route('/api/websocket/<websocket_uuid>/ltp', methods=['POST'])
def receive_ltp_tick(websocket_uuid):
    """Endpoint to receive LTP tick data from Flask worker matching LtpDataDto"""
    try:
        data = request.get_json()
        websocket_id = data.get('websocket_id')
        tick = data.get('tick')  # This should be LtpTickDto format
        timestamp = data.get('timestamp')  # Optional timestamp from sender
        
        # Validate websocket_uuid matches
        if websocket_id != websocket_uuid:
            return jsonify({
                'status': 'error', 
                'message': f'WebSocket UUID mismatch: {websocket_id} != {websocket_uuid}'
            }), 400
        
        # Add our own timestamp for processing
        tick_with_metadata = {
            'received_at': datetime.now().isoformat(),
            'websocket_id': websocket_id,
            'tick': tick,
            'sender_timestamp': timestamp  # From Flask worker
        }
        
        received_ticks.append(tick_with_metadata)
        
        # Print tick (simulating processing) - show key fields
        token = tick.get('token', 'unknown')
        ltp = tick.get('last_traded_price', 0)
        print(f"📈 LTP Tick: Token={token}, Price={ltp/100:.2f}, WebSocket={websocket_id}")
        
        return jsonify({'status': 'success', 'message': 'LTP tick received'})
        
    except Exception as e:
        print(f"❌ Error processing LTP tick: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/ticks', methods=['GET'])
def get_received_ticks():
    """Get all received ticks for testing"""
    return jsonify({
        'total_ticks': len(received_ticks),
        'ticks': received_ticks[-10:]  # Return last 10 ticks
    })

@app.route('/api/clear', methods=['POST'])
def clear_ticks():
    """Clear all received ticks"""
    global received_ticks
    received_ticks = []
    return jsonify({'status': 'success', 'message': 'Ticks cleared'})

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'mock-backend',
        'total_ticks_received': len(received_ticks)
    })

if __name__ == '__main__':
    print("🚀 Starting mock backend server on port 3000...")
    print("📊 LTP Tick endpoint: http://localhost:3000/api/websocket/{websocket_uuid}/ltp")
    print("📈 View ticks: http://localhost:3000/api/ticks")
    app.run(host='0.0.0.0', port=3000, debug=True)
