import cv2
import threading
import time
from vision.emotion_detector import EmotionDetector
from vision.posture_detector import PostureDetector
from utils.logger import get_logger

logger = get_logger(__name__)

class JarvisVideoProcessor:
    def __init__(self):
        self.latest_emotion = "neutral"
        self.latest_emotion_conf = 0.0
        self.latest_posture = "unknown"
        self.latest_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._frame_count = 0
        self._emotion_detector = EmotionDetector()
        self._posture_detector = PostureDetector()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Video processor started.")

    def stop(self):
        self._running = False
        logger.info("Video processor stopped.")

    def _capture_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Could not open webcam.")
            self._running = False
            return
        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            self._frame_count += 1
            annotated = frame.copy()
            if self._frame_count % 10 == 0:
                try:
                    posture, annotated = self._posture_detector.detect_posture(frame)
                    emotion, conf = self._emotion_detector.detect_emotion(frame)
                    with self._lock:
                        self.latest_emotion = emotion
                        self.latest_emotion_conf = conf
                        self.latest_posture = posture
                except Exception as e:
                    logger.error(f"Detection error: {e}")
            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            with self._lock:
                self.latest_frame = frame_rgb
            time.sleep(0.033)
        cap.release()

    def get_frame(self):
        with self._lock:
            return self.latest_frame

    def get_state(self):
        with self._lock:
            return (
                self.latest_emotion,
                self.latest_emotion_conf,
                self.latest_posture
            )
