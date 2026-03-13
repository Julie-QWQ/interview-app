#!/bin/bash
# AI Interview System - One-Click Startup Script

echo "========================================"
echo "  AI Interview System - Startup"
echo "========================================"
echo ""

# 1. Start database
echo "[1/3] Starting database..."
./scripts/start-db.sh
if [ $? -ne 0 ]; then
    echo "[ERROR] Database startup failed"
    exit 1
fi

echo ""
echo "[INFO] Waiting for database to be fully ready..."
sleep 5

# 2. Start backend
echo ""
echo "[2/3] Starting backend service..."
cd backend

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment with uv..."
    uv venv
fi

echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found"
    echo "  Copy .env.example to .env and configure it"
    echo "  Command: cp .env.example .env"
    echo ""
fi

echo "[INFO] Installing dependencies with uv..."
uv sync --frozen

echo "[INFO] Bootstrapping database schema..."
python scripts/migration_manager.py migrate
if [ $? -ne 0 ]; then
    echo "[ERROR] Database bootstrap failed"
    cd ..
    exit 1
fi

echo "[INFO] Starting backend service (port 8000 via uvicorn)..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "[SUCCESS] Backend service started (PID: $BACKEND_PID)"

# 3. Start frontend
echo ""
echo "[3/3] Starting frontend service..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing dependencies..."
    npm install
fi

echo "[INFO] Starting frontend dev server (port 5173)..."
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "========================================"
echo "  All Services Started Successfully!"
echo "========================================"
echo ""
echo "Access URLs:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo ""
echo "Tips: Press Ctrl+C to stop all services"
echo "========================================"

# Wait for user interrupt
trap "echo ''; echo '[INFO] Stopping all services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
