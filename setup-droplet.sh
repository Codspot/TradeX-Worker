#!/bin/bash

# DigitalOcean Droplet Setup Script for SmartAPI Worker
# Run this on your DigitalOcean droplet after cloning the repository

echo "🌊 DigitalOcean SmartAPI Worker Setup"
echo "====================================="

# Get the current working directory
CURRENT_DIR=$(pwd)
echo "📂 Current directory: $CURRENT_DIR"

# Update package lists
echo "📦 Updating system packages..."
sudo apt update

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt install -y python3-pip python3-venv nodejs npm curl

# Install PM2 globally
echo "⚙️  Installing PM2..."
sudo npm install -g pm2

# Navigate to worker directory (adjust path as needed)
WORKER_DIR="/path/to/your/smartapi_candle_tracker"
if [ -d "./smartapi_candle_tracker" ]; then
    WORKER_DIR="./smartapi_candle_tracker"
    echo "✅ Found smartapi_candle_tracker in current directory"
elif [ -d "../smartapi_candle_tracker" ]; then
    WORKER_DIR="../smartapi_candle_tracker"
    echo "✅ Found smartapi_candle_tracker in parent directory"
else
    echo "❌ Please update WORKER_DIR path in this script to point to your smartapi_candle_tracker directory"
    echo "Current structure:"
    ls -la
    exit 1
fi

cd "$WORKER_DIR"
echo "📂 Working in: $(pwd)"

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "❌ No .env.example found. Please create .env file manually"
        exit 1
    fi
fi

echo "📝 Please update your .env file with:"
echo "   - Your SmartAPI credentials"
echo "   - Correct backend URLs (use your droplet's IP if needed)"
echo ""
echo "Current .env file:"
cat .env

echo ""
echo "✅ Setup completed!"
echo ""
echo "🚀 Next steps:"
echo "1. Update .env with your credentials:"
echo "   nano .env"
echo ""
echo "2. Deploy with PM2:"
echo "   ./deploy-pm2.sh"
echo ""
echo "3. Check status:"
echo "   ./check-status.sh"
echo ""
echo "4. View logs:"
echo "   pm2 logs smartapi-worker"
