#!/bin/bash

# ActiveMotion Quick Start Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure script runs only on Linux or macOS
if [[ "$OSTYPE" != "linux-gnu"* && "$OSTYPE" != "darwin"* ]]; then
    echo -e "${YELLOW}⚠️  This script is only supported on Linux or macOS.${NC}"
    exit 1
fi

set -e

echo -e "${BLUE}🚀 ActiveMotion Startup Script${NC}"
echo ""

# Check if running from the correct directory
if [ ! -f "README.md" ] || [ ! -d "Backend" ] || [ ! -d "Frontend" ]; then
    echo -e "${YELLOW}⚠️  Please run this script from the ActiveMotion root directory${NC}"
    exit 1
fi

# Start Backend
echo -e "${BLUE}1️⃣  Starting Backend Server...${NC}"
echo "   Backend will run on http://localhost:8000"
cd Backend

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}   Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt

# Start the backend in the background
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2
echo -e "${GREEN}   ✅ Backend started (PID: $BACKEND_PID)${NC}"
echo ""

# Start Frontend
echo -e "${BLUE}2️⃣  Starting Frontend...${NC}"
echo "   Frontend will run on http://localhost:5173"
cd ../Frontend

# Check and install npm dependencies
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}   Installing npm dependencies...${NC}"
    npm install --silent
fi

npm run dev &
FRONTEND_PID=$!

sleep 3
echo -e "${GREEN}   ✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo ""

echo -e "${GREEN}🎉 ActiveMotion is ready!${NC}"
echo ""
echo -e "📍 Frontend:  ${BLUE}http://localhost:5173${NC}"
echo -e "📍 Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "📍 API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "To stop: Press Ctrl+C"
echo ""

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}All services stopped${NC}"
}

trap cleanup EXIT

# Keep the script running
wait
