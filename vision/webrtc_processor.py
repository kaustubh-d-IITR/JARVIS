import os
import cv2
import numpy as np
from datetime import datetime
from PIL import Image
from utils.logger import get_logger

logger = get_logger(__name__)

class JarvisVideoProcessor:
    """
    Lightweight Image Processing Utility.
    Handles saving browser-captured snapshots to disk.
    """
    def __init__(self):
        self.output_dir = "captured_frames"
        os.makedirs(self.output_dir, exist_ok=True)

    def save_snapshot(self, image_data) -> str:
        """
        Saves a snapshot from st.camera_input to the session directory.
        Overwrites a single file to prevent Streamlit Cloud storage bloat.
        Returns the absolute path to the saved image.
        """
        try:
            file_path = os.path.join(self.output_dir, "latest_snapshot.jpg")
            
            # image_data is a UploadedFile-like object from st.camera_input
            img = Image.open(image_data)
            img.save(file_path, "JPEG")
            
            logger.info(f"[CAMERA] Snapshot saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"[CAMERA] Failed to save snapshot: {e}")
            return ""

    def pil_to_cv2(self, pil_image):
        """Helper to convert PIL image to OpenCV format if needed."""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def get_debug_state(self):
        """Minimal debug state for the new architecture."""
        return {
            "mode": "browser_snapshot",
            "storage_ready": os.path.exists(self.output_dir)
        }
