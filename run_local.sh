#!/bin/bash
echo "Running JARVIS Startup Checks..."
python startup_check.py

echo ""
echo "Starting Streamlit App..."
streamlit run app.py
