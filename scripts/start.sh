#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "  ========================================"
echo "    SlideForge v0.1.0"
echo "    Local AI PPT Generator"
echo "  ========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Create venv if needed
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "[SETUP] First run: creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
    source "$PROJECT_DIR/venv/bin/activate"
    echo "[SETUP] Installing Python dependencies..."
    pip install -r "$PROJECT_DIR/backend/requirements.txt"
else
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Build frontend if needed
if [ ! -f "$PROJECT_DIR/frontend/dist/index.html" ]; then
    echo "[BUILD] Building frontend..."
    cd "$PROJECT_DIR/frontend"
    npm install
    npm run build
fi

echo "[START] Starting SlideForge server..."
echo "[URL] Open browser: http://localhost:5000"
echo ""
cd "$PROJECT_DIR/backend"
python app.py
