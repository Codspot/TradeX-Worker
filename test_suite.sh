#!/bin/bash

# Comprehensive test script for Flask API
echo "🧪 Flask API Test Suite"
echo "======================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    local port=$3
    
    echo -e "${YELLOW}🚀 Starting $name...${NC}"
    
    if check_port $port; then
        echo -e "${GREEN}✅ $name already running on port $port${NC}"
    else
        eval $command &
        local pid=$!
        echo "PID $pid saved for $name"
        
        # Wait for service to start
        sleep 3
        
        if check_port $port; then
            echo -e "${GREEN}✅ $name started successfully on port $port${NC}"
        else
            echo -e "${RED}❌ Failed to start $name${NC}"
            return 1
        fi
    fi
}

# Function to cleanup background processes
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up background processes...${NC}"
    # Kill any Python processes we might have started
    pkill -f "mock_backend.py" 2>/dev/null || true
    pkill -f "run.py" 2>/dev/null || true
    exit 0
}

# Trap to cleanup on script exit
trap cleanup EXIT INT TERM

echo "📋 Test Plan:"
echo "1. Start Mock Backend Server (port 3000)"
echo "2. Start Flask Worker (port 5000)"
echo "3. Run API Tests"
echo ""

# Step 1: Start Mock Backend
start_service "Mock Backend" "python3 mock_backend.py" 3000

echo ""

# Step 2: Start Flask Worker
start_service "Flask Worker" "python3 run.py" 5000

echo ""

# Step 3: Wait a bit more for everything to be ready
echo -e "${YELLOW}⏳ Waiting 5 seconds for services to be fully ready...${NC}"
sleep 5

# Step 4: Run the tests
echo -e "${YELLOW}🧪 Running API tests...${NC}"
echo "================================"
python3 test_flask_api.py

echo ""
echo "================================"
echo -e "${GREEN}🏁 Test suite completed!${NC}"

# Show some helpful URLs
echo ""
echo "📊 Useful endpoints:"
echo "• Flask Health: http://localhost:5000/api/health"
echo "• Flask Status: http://localhost:5000/api/status"
echo "• Mock Backend Health: http://localhost:3000/health"
echo "• View Received Ticks: http://localhost:3000/api/ticks"

echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services and exit${NC}"

# Keep the script running to maintain the services
while true; do
    sleep 1
done
