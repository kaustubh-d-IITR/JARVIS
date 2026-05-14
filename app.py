import streamlit as st
import sys
import asyncio
from ui.dashboard import render_dashboard

# Ensure asyncio loop exists for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    try:
        render_dashboard()
    except Exception as e:
        st.error(f"Application error during rendering: {e}")
