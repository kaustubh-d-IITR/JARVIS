#!/bin/bash
echo ""
echo "================================================"
echo "  JARVIS — Automated Local Setup (Linux/Mac)"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install Python 3.10+ first."
    exit 1
fi

echo "[1/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "      Virtual environment created."
else
    echo "      Virtual environment already exists."
fi

echo "[2/5] Activating virtual environment..."
source venv/bin/activate

echo "[3/5] Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo "[4/5] Verifying key files..."
if [ ! -f "vision/fer_checkpoint.tar" ]; then
    echo ""
    echo "[WARNING] vision/fer_checkpoint.tar NOT FOUND!"
    echo "         Download and place it at: JARVIS/vision/fer_checkpoint.tar"
    echo ""
fi
if [ ! -f ".env" ]; then
    echo ""
    echo "[WARNING] .env file NOT FOUND!"
    echo "         Create .env with your API keys."
    echo ""
fi

echo "[5/5] Running startup validation..."
python startup_check.py

echo ""
echo "================================================"
echo "  Setup complete. Run: ./run_jarvis.sh"
echo "================================================"
