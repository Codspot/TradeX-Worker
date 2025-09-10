#!/bin/bash

# SmartAPI Worker Status Check Script

echo "🔍 SmartAPI Worker Status Check"
echo "==============================="

# Check PM2 status
echo "📊 PM2 Process Status:"
pm2 status smartapi-worker 2>/dev/null || echo "❌ SmartAPI worker is not running in PM2"

echo ""

# Check if the worker is responding
echo "🌐 Health Check:"
WORKER_URL="http://localhost:5000"
if curl -s "$WORKER_URL" > /dev/null; then
    echo "✅ Worker is responding at $WORKER_URL"
else
    echo "❌ Worker is not responding at $WORKER_URL"
fi

echo ""

# Check backend connection
echo "🔗 Backend Connection Check:"
BACKEND_URL="http://localhost:3000/api/in-memory-candles/stats"
if curl -s "$BACKEND_URL" > /dev/null; then
    echo "✅ Backend is responding at $BACKEND_URL"
    echo "📊 Backend Stats:"
    curl -s "$BACKEND_URL" | python3 -m json.tool 2>/dev/null || echo "   Could not parse response"
else
    echo "❌ Backend is not responding at $BACKEND_URL"
fi

echo ""

# Show recent logs
echo "📋 Recent Logs (last 20 lines):"
pm2 logs smartapi-worker --lines 20 --nostream 2>/dev/null || echo "❌ Could not retrieve logs"

echo ""
echo "🎯 Quick Commands:"
echo "   ./deploy-pm2.sh           - Deploy/redeploy the worker"
echo "   pm2 logs smartapi-worker  - View live logs"
echo "   pm2 restart smartapi-worker - Restart the worker"
