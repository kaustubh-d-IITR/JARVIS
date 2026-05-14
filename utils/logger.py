import logging
import sys

class StreamlitSessionHandler(logging.Handler):
    def emit(self, record):
        try:
            import streamlit as st
            msg = self.format(record)
            if 'system_logs' not in st.session_state:
                st.session_state.system_logs = []
            st.session_state.system_logs.insert(0, msg)
            if len(st.session_state.system_logs) > 50:
                st.session_state.system_logs.pop()
        except Exception:
            pass # Ignore if not running in Streamlit context

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance that writes to stdout and Streamlit.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Create Streamlit handler
        st_handler = StreamlitSessionHandler()
        st_handler.setLevel(logging.INFO)
        st_formatter = logging.Formatter('%(name)s: %(message)s')
        st_handler.setFormatter(st_formatter)
        logger.addHandler(st_handler)
        
    return logger
