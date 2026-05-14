import cv2
import threading
import time
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class CameraManager:
    def __init__(self, posture_detector, emotion_detector):
        self.cap = None
        self.running = False
        self.thread = None
        
        self.posture_detector = posture_detector
        self.emotion_detector = emotion_detector
        
        self.latest_frame_rgb = None
        self.latest_emotion = "neutral"
        self.latest_emotion_conf = 0.0
        self.latest_posture = "unknown"
        self.status = "Initializing..."
        
        self.lock = threading.Lock()
        
    def start(self):
        if self.running:
            return True
            
        self.cap = cv2.VideoCapture(settings.CAMERA_INDEX)
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera at index {settings.CAMERA_INDEX}")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("Background camera thread started.")
        return True
        
    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Background camera thread stopped.")
            
    def _update_loop(self):
        with self.lock:
            self.status = "Opening hardware camera..."
        
        while self.running and self.cap and self.cap.isOpened():
            with self.lock:
                self.status = "Reading frame from camera..."
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
                
            # Perform heavy CV processing in the background thread
            with self.lock:
                self.status = "Detecting Body Posture (MediaPipe)..."
            posture, annotated_frame = self.posture_detector.detect_posture(frame)
            
            with self.lock:
                self.status = "Detecting Emotion (DeepFace) - This takes a while on first run to download weights!"
            try:
                emotion, conf = self.emotion_detector.detect_emotion(annotated_frame)
            except Exception as e:
                logger.error(f"Emotion detection failed: {e}")
                emotion, conf = "neutral", 0.0
            
            with self.lock:
                self.status = "Processing complete. Updating UI..."
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            # Safely update the latest variables
            with self.lock:
                self.latest_frame_rgb = frame_rgb
                self.latest_emotion = emotion
                self.latest_emotion_conf = conf
                self.latest_posture = posture
                
            # Sleep slightly to prevent 100% CPU usage
            time.sleep(0.05)
            
    def get_latest_data(self):
        """Returns the most recent processed frame and metrics safely."""
        with self.lock:
            return (
                self.latest_frame_rgb,
                self.latest_emotion,
                self.latest_emotion_conf,
                self.latest_posture,
                self.status
            )
