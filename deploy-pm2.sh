#!/bin/bash

# PM2 Deployment Script for SmartAPI Worker
# This script helps deploy the SmartAPI worker to your DigitalOcean droplet using PM2

set -e  # Exit on any error

echo "🚀 SmartAPI Worker PM2 Deployment Script"
echo "=========================================="

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "❌ PM2 is not installed. Installing PM2..."
    npm install -g pm2
    echo "✅ PM2 installed successfully"
fi

# Navigate to the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📂 Working directory: $(pwd)"

# Check Python dependencies
echo "🐍 Checking Python dependencies..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Please create one based on .env.example"
    exit 1
fi

echo "✅ Environment file found"

# Validate the configuration
echo "🔧 Validating configuration..."
python3 -c "
import sys
sys.path.append('.')
try:
    from app.config import config
    print(f'✅ Configuration loaded successfully')
    print(f'   Environment: {config.ENV}')
    print(f'   Worker Port: {config.WORKER_PORT}')
    print(f'   Backend URL: {config.BACKEND_BASE_URL}')
    print(f'   Webhook URL: {config.BACKEND_WEBHOOK_URL}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"

# Stop existing PM2 process if running
echo "🛑 Stopping existing SmartAPI worker..."
pm2 stop smartapi-worker 2>/dev/null || echo "   No existing process found"
pm2 delete smartapi-worker 2>/dev/null || echo "   No existing process to delete"

# Start the application with PM2
echo "🚀 Starting SmartAPI worker with PM2..."
pm2 start ecosystem.config.js --env production

# Save PM2 configuration
echo "💾 Saving PM2 configuration..."
pm2 save

# Setup PM2 startup script (for auto-restart on server reboot)
echo "⚙️  Setting up PM2 startup script..."
pm2 startup || echo "   Startup script setup may require manual action"

# Show status
echo "📊 PM2 Status:"
pm2 status

echo ""
echo "✅ SmartAPI Worker deployment completed!"
echo ""
echo "📋 Useful PM2 commands:"
echo "   pm2 status                    - View all processes"
echo "   pm2 logs smartapi-worker      - View logs"
echo "   pm2 restart smartapi-worker   - Restart the worker"
echo "   pm2 stop smartapi-worker      - Stop the worker"
echo "   pm2 delete smartapi-worker    - Remove the worker"
echo ""
echo "🌐 Worker should be running on: http://localhost:5000"
echo "📡 Backend webhook URL: $(python3 -c 'from app.config import config; print(config.BACKEND_WEBHOOK_URL)')"
