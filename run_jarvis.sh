#!/bin/bash
echo ""
echo "================================================"
echo "  JARVIS — Launching..."
echo "================================================"
echo ""

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run startup check
echo "[1/2] Running pre-flight checks..."
python startup_check.py
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Startup checks failed. Fix errors above first."
    echo "        Run ./setup_local.sh to install dependencies."
    exit 1
fi

# Launch Streamlit
echo ""
echo "[2/2] Starting JARVIS..."
echo ""
echo "  Opening browser at http://127.0.0.1:8501"
echo "  Press Ctrl+C to stop."
echo ""
streamlit run app.py --server.port 8501 --browser.serverAddress localhost
