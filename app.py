import streamlit as st
import sys
import asyncio
from startup_check import run_all_checks
from ui.dashboard import render_dashboard

# Ensure asyncio loop exists for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    # Optional console validation before rendering
    # run_all_checks() prints to console, we just call it silently
    try:
        render_dashboard()
    except Exception as e:
        st.error(f"Application error during rendering: {e}")
